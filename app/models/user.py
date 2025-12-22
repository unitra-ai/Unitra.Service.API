"""User model re-export for backward compatibility.

The actual User model is now in app.auth.models to integrate with FastAPI-Users.
"""

from app.auth.models import TIER_LIMITS, User, UserTier

__all__ = ["User", "UserTier", "TIER_LIMITS"]
