# app/core/auth.py

from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    # bcrypt max is 72 bytes — truncate to avoid ValueError
    return pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)


def create_access_token(user_id: str, tier: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "tier": tier, "exp": expire, "type": "access"},
        settings.secret_key, algorithm=ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh"},
        settings.secret_key, algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[dict]:
    if token is None:
        return None
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def require_auth(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_paid(user: dict = Depends(require_auth)) -> dict:
    if user.get("tier") not in ("paid", "admin"):
        raise HTTPException(status_code=403, detail="Paid subscription required")
    return user


async def require_admin(user: dict = Depends(require_auth)) -> dict:
    if user.get("tier") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
