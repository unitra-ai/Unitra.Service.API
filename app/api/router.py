"""Main API router."""

from fastapi import APIRouter

from app.api.v1 import auth, translate, usage, health

api_router = APIRouter()

# Health check (no version prefix)
api_router.include_router(health.router, tags=["health"])

# V1 API routes
api_router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
api_router.include_router(translate.router, prefix="/v1", tags=["translate"])
api_router.include_router(usage.router, prefix="/v1", tags=["usage"])
