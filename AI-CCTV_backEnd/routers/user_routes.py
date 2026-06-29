"""
user_routes.py — User management endpoints: register, admin password reset.
"""

import logging
import secrets
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from service import app_state
from service.auth import TokenClaims, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Users"])


# ──────────────────────────────────────────────
#  POST /users/register
# ──────────────────────────────────────────────
class UserRegisterIn(BaseModel):
    username: str
    password: str
    department: str
    is_admin: bool = False
    access: Optional[List[str]] = None


@router.post("/users/register")
def register_user(user: UserRegisterIn, _: TokenClaims = Depends(require_admin)):
    db = app_state.db
    access = user.access or []
    if user.is_admin and "admin" not in access:
        access.append("admin")
    try:
        ok = db.register_user(
            username=user.username,
            password=user.password,
            department=user.department,
            is_admin=user.is_admin,
            access=access,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    if not ok:
        raise HTTPException(status_code=409, detail="User already exists")
    return {"ok": True, "username": user.username}


# ──────────────────────────────────────────────
#  POST /admin/reset-password
# ──────────────────────────────────────────────
class AdminResetPasswordIn(BaseModel):
    username: str


@router.post("/admin/reset-password")
def admin_reset_password(
    payload: AdminResetPasswordIn, _: TokenClaims = Depends(require_admin)
):
    db = app_state.db
    username = (payload.username or "").strip()
    if not username:
        raise HTTPException(400, "username is required")

    temp_password = secrets.token_urlsafe(12)
    ok = db.set_temp_password(username, temp_password)
    if not ok:
        raise HTTPException(404, f"User '{username}' not found or failed to set temp password")

    return {
        "ok": True,
        "username": username,
        "temp_password": temp_password,
        "message": f"User '{username}' has been assigned a temporary password.",
    }


# ──────────────────────────────────────────────
#  GET /users
# ──────────────────────────────────────────────
@router.get("/users")
def list_users(_: TokenClaims = Depends(require_admin)):
    db = app_state.db
    try:
        return db.list_users()
    except Exception as e:
        raise HTTPException(500, f"Error listing users: {e}")


# ──────────────────────────────────────────────
#  PUT /users/{username}
# ──────────────────────────────────────────────
class UserUpdateIn(BaseModel):
    department: Optional[str] = None
    is_admin: Optional[bool] = None
    access: Optional[List[str]] = None
    password: Optional[str] = None


@router.put("/users/{username}")
def update_user(
    username: str, payload: UserUpdateIn, _: TokenClaims = Depends(require_admin)
):
    db = app_state.db
    updates = {}
    if payload.department is not None:
        updates["department"] = payload.department
    if payload.is_admin is not None:
        updates["is_admin"] = payload.is_admin
    if payload.access is not None:
        updates["access"] = payload.access
    if payload.password is not None:
        updates["password"] = payload.password
    if not updates:
        return {"ok": True}
    try:
        ok = db.update_user(username, updates)
        if not ok:
            raise HTTPException(404, "User not found")
    except Exception as e:
        raise HTTPException(500, f"Error updating user: {e}")
    return {"ok": True, "username": username}


# ──────────────────────────────────────────────
#  DELETE /users/{username}
# ──────────────────────────────────────────────
@router.delete("/users/{username}")
def delete_user(username: str, _: TokenClaims = Depends(require_admin)):
    db = app_state.db
    try:
        ok = db.delete_user(username)
        if not ok:
            raise HTTPException(404, "User not found")
    except Exception as e:
        raise HTTPException(500, f"Error deleting user: {e}")
    return {"ok": True, "username": username}
