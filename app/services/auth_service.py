# app/services/auth_service.py

from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.database import get_db
from app.models.schemas import RegisterRequest, TokenResponse


async def register_user(body: RegisterRequest) -> dict:
    db = get_db()
    existing = await db.users.find_one(
        {"$or": [{"email": body.email}, {"username": body.username}]}
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already registered")

    user = {
        "email": body.email,
        "username": body.username,
        "hashed_password": hash_password(body.password),
        "tier": "free",
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.utcnow(),
    }
    result = await db.users.insert_one(user)
    user["_id"] = result.inserted_id
    return user


async def login_user(username_or_email: str, password: str) -> TokenResponse:
    db = get_db()
    user = await db.users.find_one(
        {"$or": [{"email": username_or_email}, {"username": username_or_email}]}
    )
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")

    uid = str(user["_id"])
    return TokenResponse(
        access_token=create_access_token(uid, user["tier"]),
        refresh_token=create_refresh_token(uid),
        tier=user["tier"],
    )


async def refresh_tokens(refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User not found or inactive")

    uid = str(user["_id"])
    return TokenResponse(
        access_token=create_access_token(uid, user["tier"]),
        refresh_token=create_refresh_token(uid),
        tier=user["tier"],
    )
