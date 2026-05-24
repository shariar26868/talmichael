# app/routes/auth.py

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import require_auth
from app.models.schemas import RegisterRequest, TokenResponse, RefreshRequest, UserProfile
from app.services.auth_service import register_user, login_user, refresh_tokens

router = APIRouter(prefix="/auth", tags=["Auth"])


def _to_profile(user: dict) -> dict:
    return {
        "id": str(user.get("_id", "")),
        "email": user["email"],
        "username": user["username"],
        "tier": user.get("tier", "free"),
        "is_verified": user.get("is_verified", False),
    }


@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    user = await register_user(body)
    return _to_profile(user)


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    return await login_user(form.username, form.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    return await refresh_tokens(body.refresh_token)


@router.get("/me")
async def me(user: dict = Depends(require_auth)):
    return _to_profile(user)
