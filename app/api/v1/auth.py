"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    """Registration request body."""

    email: EmailStr
    password: str
    name: str


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    name: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate user and return tokens.

    TODO: Implement actual authentication.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest) -> UserResponse:
    """Register a new user.

    TODO: Implement actual registration.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str) -> TokenResponse:
    """Refresh access token.

    TODO: Implement token refresh.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/logout")
async def logout() -> dict[str, str]:
    """Logout user (invalidate tokens).

    TODO: Implement token invalidation.
    """
    raise HTTPException(status_code=501, detail="Not implemented")
