"""Authentication module using FastAPI-Users."""

from app.auth.backend import auth_backend, fastapi_users
from app.auth.models import User, UserTier
from app.auth.schemas import UserCreate, UserRead, UserUpdate

__all__ = [
    "User",
    "UserTier",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "auth_backend",
    "fastapi_users",
]
