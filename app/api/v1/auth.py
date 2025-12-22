"""Authentication endpoints using FastAPI-Users.

This module re-exports the auth routers from the auth module.
"""

from app.auth.router import get_auth_router, get_users_router

# Main auth router with all authentication endpoints
router = get_auth_router()

# Users router for user management
users_router = get_users_router()
