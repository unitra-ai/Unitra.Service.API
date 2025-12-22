"""Main API router."""

from fastapi import APIRouter

from app.api.v1 import auth, billing, health, translate, usage

api_router = APIRouter()

# Health check (no version prefix)
api_router.include_router(
    health.router,
    tags=["Health"],
)

# V1 API routes
# Authentication routes (FastAPI-Users)
api_router.include_router(
    auth.router,
    prefix="/v1/auth",
    tags=["Authentication"],
)
# User management routes (FastAPI-Users)
api_router.include_router(
    auth.users_router,
    prefix="/v1/users",
    tags=["Users"],
)
api_router.include_router(
    translate.router,
    prefix="/v1/translate",
    tags=["Translation"],
)
api_router.include_router(
    usage.router,
    prefix="/v1/usage",
    tags=["Usage"],
)
api_router.include_router(
    billing.router,
    prefix="/v1/billing",
    tags=["Billing"],
)
