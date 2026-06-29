"""
auth_routes.py — Authentication endpoints: login, logout, temp-login, change-password.
"""

import logging
import secrets
from typing import List, Optional

import jwt
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from service import app_state, utils
from service.auth import (
    TokenClaims,
    create_access_token,
    create_temp_login_token,
    require_user,
    session_has_active,
    session_is_active,
    session_register,
    session_revoke_one,
    session_revoke_user,
)
from service.config import JWT_ALG, JWT_EXPIRE_MINUTES, JWT_SECRET

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"])


# ──────────────────────────────────────────────
#  POST /auth/login
# ──────────────────────────────────────────────
@router.post("/auth/login")
def auth_login(
    payload: dict = Body(...),
    force: bool = Query(False),
    remember: bool = Query(False),
    request: Request = None,
):
    db = app_state.db
    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="username/password required")

    res = db.check_user(username, password)
    if isinstance(res, tuple) and len(res) == 4:
        is_valid, department, access, is_admin = res
    elif isinstance(res, tuple) and len(res) == 3:
        is_valid, department, access = res
        is_admin = department == "IT"
    else:
        raise HTTPException(500, "check_user returned unexpected format")

    if not is_valid:
        raise HTTPException(status_code=401, detail="user or password wrong")

    if session_has_active(username) and not force:
        raise HTTPException(409, "User already logged in on another device")
    if force:
        session_revoke_user(username)

    access_list = (
        [x.strip() for x in access.split(",") if x.strip()]
        if isinstance(access, str)
        else list(access or [])
    )

    ttl = (60 * 24 * 7) if remember else JWT_EXPIRE_MINUTES
    token = create_access_token(username, department, access_list, bool(is_admin), ttl_minutes=ttl)

    try:
        pl = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        ua = request.headers.get("user-agent", "") if request else ""
        ip = request.client.host if (request and request.client) else None
        session_register(username, pl.get("sid"), pl.get("jti"), pl.get("exp"), ua, ip)
    except Exception as e:
        raise HTTPException(500, f"session register failed: {e}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "department": department,
        "access": access_list,
        "is_admin": bool(is_admin),
        "expires_in": (ttl * 60),
    }


# ──────────────────────────────────────────────
#  POST /auth/logout
# ──────────────────────────────────────────────
@router.post("/auth/logout")
def auth_logout(claims: TokenClaims = Depends(require_user)):
    try:
        session_revoke_one(claims.sub, claims.sid or "")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"logout failed: {e}")


@router.post("/auth/logout-all")
def auth_logout_all(claims: TokenClaims = Depends(require_user)):
    try:
        session_revoke_user(claims.sub)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"logout all failed: {e}")


# ──────────────────────────────────────────────
#  POST /auth/login-temp
# ──────────────────────────────────────────────
class LoginTempIn(BaseModel):
    username: str
    temp_password: str


@router.post("/auth/login-temp")
def auth_login_temp(payload: LoginTempIn, request: Request = None):
    db = app_state.db
    username = (payload.username or "").strip()
    temp_password = (payload.temp_password or "").strip()
    if not username or not temp_password:
        raise HTTPException(400, "username/temp_password required")

    valid, reason = db.verify_temp_password(username, temp_password)
    if not valid:
        raise HTTPException(401, f"temp login failed: {reason}")

    token = create_temp_login_token(username)
    try:
        pl = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        sid, jti, exp = pl.get("sid"), pl.get("jti"), pl.get("exp")
        if sid and jti and exp:
            ua = request.headers.get("user-agent", "") if request else ""
            ip = request.client.host if (request and request.client) else None
            session_register(username, sid, jti, exp, ua, ip)
    except Exception as e:
        logger.error(f"[TEMP LOGIN] Session register failed: {e}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": True,
        "expires_in": 30 * 60,
    }


# ──────────────────────────────────────────────
#  POST /auth/change-password
# ──────────────────────────────────────────────
class ChangePasswordIn(BaseModel):
    new_password: str


@router.post("/auth/change-password")
def auth_change_password(
    payload: ChangePasswordIn, claims: TokenClaims = Depends(require_user)
):
    db = app_state.db
    new_pw = (payload.new_password or "").strip()
    if not new_pw or len(new_pw) < 6:
        raise HTTPException(422, "new_password is too short (min 6 chars)")

    username = claims.sub
    if not claims.must_change:
        raise HTTPException(403, "Forbidden: Action requires temporary password state.")

    try:
        consume_ok = db.consume_temp_password(username, new_pw)
        if not consume_ok:
            raise HTTPException(500, "Failed to set new password in database.")
    except HTTPException:
        raise
    except Exception as db_err:
        raise HTTPException(500, f"Database error during password update: {db_err}")

    try:
        prof = db.get_user_profile(username) or {}
        dept = prof.get("department", "")
        access_raw = prof.get("access")
        if isinstance(access_raw, list):
            access = access_raw
        elif isinstance(access_raw, str):
            access = [x.strip() for x in access_raw.split(",") if x.strip()]
        else:
            access = []
        is_admin = bool(prof.get("is_admin", False))
        new_token = create_access_token(username, dept, access, is_admin)
    except Exception as token_err:
        raise HTTPException(
            500, "Password updated, but failed to create new session token. Please log in again."
        )

    try:
        pl = jwt.decode(new_token, JWT_SECRET, algorithms=[JWT_ALG])
        new_sid, new_jti, new_exp = pl.get("sid"), pl.get("jti"), pl.get("exp")
        if not new_sid or not new_jti or not new_exp:
            raise HTTPException(500, "Internal error: New token structure invalid.")
        session_register(username, new_sid, new_jti, new_exp)
    except jwt.PyJWTError:
        raise HTTPException(500, "Password updated, but token processing failed. Please log in again.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "Password updated, but session registration failed. Please log in again.")

    return {
        "ok": True,
        "message": "Password changed successfully. Use this new token.",
        "access_token": new_token,
        "token_type": "bearer",
        "department": dept,
        "access": access,
        "is_admin": is_admin,
    }
