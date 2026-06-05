"""
auth.py — JWT helpers, session management, and FastAPI authentication dependencies.
"""

import datetime as dt
import logging
import uuid
from typing import Dict, List, Optional

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from service import app_state
from service.config import JWT_ALG, JWT_EXPIRE_MINUTES, JWT_SECRET, TZ

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


# ──────────────────────────────────────────────
#  Token Claims Model
# ──────────────────────────────────────────────
class TokenClaims(BaseModel):
    sub: str
    department: str = ""
    access: List[str] = []
    is_admin: bool = False
    iat: int
    exp: int
    must_change: bool = False
    sid: Optional[str] = None
    jti: Optional[str] = None


# ──────────────────────────────────────────────
#  Token creation
# ──────────────────────────────────────────────
def create_access_token(
    username: str,
    department: str,
    access: List[str],
    is_admin: bool,
    ttl_minutes: Optional[int] = None,
) -> str:
    now_ = dt.datetime.now(TZ)
    ttl = int(ttl_minutes if ttl_minutes is not None else JWT_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "department": department or "",
        "access": access or [],
        "is_admin": bool(is_admin),
        "must_change": False,
        "sid": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "iat": int(now_.timestamp()),
        "exp": int((now_ + dt.timedelta(minutes=ttl)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_temp_login_token(username: str) -> str:
    now_ = dt.datetime.now(TZ)
    payload = {
        "sub": username,
        "department": "",
        "access": [],
        "is_admin": False,
        "must_change": True,
        "sid": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "iat": int(now_.timestamp()),
        "exp": int((now_ + dt.timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


# ──────────────────────────────────────────────
#  Session management (DB with in-memory fallback)
# ──────────────────────────────────────────────
_active_sessions: Dict[str, dict] = {}


def _db_has_session_table() -> bool:
    db = app_state.db
    return db is not None and all(
        hasattr(db, m)
        for m in (
            "session_has_active",
            "session_register",
            "session_revoke_user",
            "session_revoke_one",
            "session_is_active",
        )
    )


def session_has_active(user: str) -> bool:
    db = app_state.db
    if db and _db_has_session_table():
        try:
            return bool(db.session_has_active(user))
        except Exception:
            pass
    ent = _active_sessions.get(user)
    if not ent:
        return False
    if ent.get("exp", 0) <= int(dt.datetime.now(TZ).timestamp()):
        _active_sessions.pop(user, None)
        return False
    return ent.get("active", False)


def session_register(
    user: str,
    sid: str,
    jti: str,
    exp: int,
    user_agent: str = "",
    ip: Optional[str] = None,
):
    db = app_state.db
    if db and _db_has_session_table():
        try:
            db.session_register(
                user_name=user, sid=sid, jti=jti, exp=exp, user_agent=user_agent, ip=ip
            )
            return
        except Exception:
            pass
    _active_sessions[user] = {"sid": sid, "jti": jti, "exp": exp, "active": True}


def session_revoke_user(user: str):
    db = app_state.db
    if db and _db_has_session_table():
        try:
            db.session_revoke_user(user)
            return
        except Exception:
            pass
    if user in _active_sessions:
        _active_sessions[user]["active"] = False


def session_revoke_one(user: str, sid: str):
    db = app_state.db
    if db and _db_has_session_table():
        try:
            db.session_revoke_one(user, sid)
            return
        except Exception:
            pass
    ent = _active_sessions.get(user)
    if ent and ent.get("sid") == sid:
        ent["active"] = False


def session_is_active(user: str, sid: str, jti: str) -> bool:
    db = app_state.db
    if db and _db_has_session_table():
        try:
            return bool(db.session_is_active(user, sid, jti))
        except Exception:
            pass
    ent = _active_sessions.get(user)
    if not ent:
        return False
    if ent.get("sid") != sid or ent.get("jti") != jti:
        return False
    if ent.get("exp", 0) <= int(dt.datetime.now(TZ).timestamp()):
        ent["active"] = False
        return False
    return ent.get("active", True)


# ──────────────────────────────────────────────
#  FastAPI dependencies — Token extraction
# ──────────────────────────────────────────────
async def get_token_from_query(
    token: str = Query(None, description="Auth token from query parameter"),
) -> Optional[str]:
    if token:
        return token
    return None


async def get_token_from_header_or_query(
    token: str = Query(None, description="Auth token from query parameter"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    if token:
        return token
    if credentials:
        return credentials.credentials
    return None


# ──────────────────────────────────────────────
#  FastAPI dependencies — Require user / admin
# ──────────────────────────────────────────────
def _validate_token(token_str: str, label: str) -> TokenClaims:
    """Common token validation logic for both HTTP and WS."""
    try:
        unverified_payload = jwt.decode(
            token_str, options={"verify_signature": False}, algorithms=[JWT_ALG]
        )
        unverified_claims = TokenClaims(**unverified_payload)
        user = unverified_claims.sub
        sid = unverified_claims.sid
        jti = unverified_claims.jti

        if not (sid and jti and user):
            raise HTTPException(status_code=401, detail="invalid_session_data_in_token")

        if not session_is_active(user, sid, jti):
            raise HTTPException(status_code=401, detail="session_revoked")

        payload = jwt.decode(token_str, JWT_SECRET, algorithms=[JWT_ALG])
        return TokenClaims(**payload)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth {label}: Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Token validation error: {e}")


async def require_user_flexible(
    token_str: Optional[str] = Depends(get_token_from_header_or_query),
) -> TokenClaims:
    if token_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (Missing Token)",
        )
    return _validate_token(token_str, "Flexible")


async def require_user_ws(
    token_str: Optional[str] = Depends(get_token_from_query),
) -> TokenClaims:
    if token_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (Missing Token)",
        )
    return _validate_token(token_str, "WS")


def require_admin_flexible(
    claims: TokenClaims = Depends(require_user_flexible),
) -> TokenClaims:
    if not claims.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator rights required",
        )
    return claims


def get_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[TokenClaims]:
    if credentials is None:
        return None
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return TokenClaims(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_user(claims: Optional[TokenClaims] = Depends(get_claims)) -> TokenClaims:
    if claims is None:
        raise HTTPException(status_code=401, detail="Missing Authorization")
    sid, jti, user = claims.sid, claims.jti, claims.sub
    if not (sid and jti and user):
        raise HTTPException(status_code=401, detail="invalid_session")
    if not session_is_active(user, sid, jti):
        raise HTTPException(status_code=401, detail="session_revoked")
    return claims


def require_admin(claims: TokenClaims = Depends(require_user)) -> TokenClaims:
    if not claims.is_admin:
        raise HTTPException(status_code=403, detail="IT admin required")
    return claims
