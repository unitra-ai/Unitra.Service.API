"""UserManager with lifecycle hooks for FastAPI-Users."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from fastapi import Request, Response
from fastapi_users import BaseUserManager, UUIDIDMixin

from app.auth.models import TIER_LIMITS, User, UserTier
from app.config import get_settings

logger = structlog.get_logger("app.auth.manager")


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    """Custom user manager with lifecycle hooks."""

    reset_password_token_secret = get_settings().secret_key
    verification_token_secret = get_settings().secret_key

    # ==========================================================================
    # Registration Hooks
    # ==========================================================================

    async def on_after_register(
        self,
        user: User,
        request: Request | None = None,
    ) -> None:
        """Handle post-registration tasks.

        - Log registration event
        - Initialize user quotas based on tier
        - TODO: Create Stripe customer
        - TODO: Send welcome email
        """
        # Set initial quota based on tier
        tier = UserTier(user.tier)
        tier_config = TIER_LIMITS.get(tier, TIER_LIMITS[UserTier.FREE])
        user.translation_minutes_limit = tier_config["minutes"]

        logger.info(
            "user_registered",
            user_id=str(user.id),
            email=user.email,
            tier=user.tier,
            minutes_limit=user.translation_minutes_limit,
        )

        # TODO: Create Stripe customer when billing is implemented
        logger.debug(
            "stripe_customer_creation_placeholder",
            user_id=str(user.id),
            message="Stripe customer creation will be implemented in billing module",
        )

        # TODO: Send welcome email when email service is configured
        logger.debug(
            "welcome_email_placeholder",
            user_id=str(user.id),
            email=user.email,
            message="Welcome email will be sent when email service is configured",
        )

    # ==========================================================================
    # Login Hooks
    # ==========================================================================

    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response: Response | None = None,
    ) -> None:
        """Handle post-login tasks.

        - Update last_login_at timestamp
        - Increment login_count
        - Log login event with IP address
        """
        # Update login tracking
        user.last_login_at = datetime.now(timezone.utc)
        user.login_count += 1

        # Get IP address from request
        ip_address = "unknown"
        if request:
            # Check for forwarded header first (for proxies)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip_address = forwarded.split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host

        logger.info(
            "user_logged_in",
            user_id=str(user.id),
            email=user.email,
            ip_address=ip_address,
            login_count=user.login_count,
        )

    # ==========================================================================
    # Password Reset Hooks
    # ==========================================================================

    async def on_after_forgot_password(
        self,
        user: User,
        token: str,
        request: Request | None = None,
    ) -> None:
        """Handle password reset request.

        - Log password reset request
        - TODO: Send reset email (for now, log token to console)
        """
        logger.info(
            "password_reset_requested",
            user_id=str(user.id),
            email=user.email,
        )

        # TODO: Send reset email when email service is configured
        # For development, log the token
        logger.warning(
            "password_reset_token_placeholder",
            user_id=str(user.id),
            token=token,
            message="Send this token via email in production",
        )

    async def on_after_reset_password(
        self,
        user: User,
        request: Request | None = None,
    ) -> None:
        """Handle successful password reset.

        - Log password change
        - TODO: Invalidate all other sessions (if using database strategy)
        """
        logger.info(
            "password_reset_completed",
            user_id=str(user.id),
            email=user.email,
        )

        # TODO: Invalidate all other sessions when session management is implemented
        logger.debug(
            "session_invalidation_placeholder",
            user_id=str(user.id),
            message="Session invalidation will be implemented with refresh token rotation",
        )

    # ==========================================================================
    # Email Verification Hooks
    # ==========================================================================

    async def on_after_request_verify(
        self,
        user: User,
        token: str,
        request: Request | None = None,
    ) -> None:
        """Handle verification token request.

        - Log verification request
        - TODO: Send verification email (for now, log token to console)
        """
        logger.info(
            "verification_requested",
            user_id=str(user.id),
            email=user.email,
        )

        # TODO: Send verification email when email service is configured
        # For development, log the token
        logger.warning(
            "verification_token_placeholder",
            user_id=str(user.id),
            token=token,
            message="Send this token via email in production",
        )

    async def on_after_verify(
        self,
        user: User,
        request: Request | None = None,
    ) -> None:
        """Handle successful email verification.

        - Log successful verification
        - TODO: Send verification success email
        """
        logger.info(
            "user_verified",
            user_id=str(user.id),
            email=user.email,
        )

        # TODO: Send verification success email
        logger.debug(
            "verification_success_email_placeholder",
            user_id=str(user.id),
            email=user.email,
            message="Verification success email will be sent when email service is configured",
        )

    # ==========================================================================
    # User Deletion Hooks
    # ==========================================================================

    async def on_before_delete(
        self,
        user: User,
        request: Request | None = None,
    ) -> None:
        """Handle pre-deletion tasks.

        - Log deletion request
        - TODO: Cancel Stripe subscription
        - TODO: Archive user data
        """
        logger.info(
            "user_deletion_requested",
            user_id=str(user.id),
            email=user.email,
            tier=user.tier,
        )

        # TODO: Cancel Stripe subscription when billing is implemented
        if user.stripe_subscription_id:
            logger.debug(
                "stripe_subscription_cancellation_placeholder",
                user_id=str(user.id),
                subscription_id=user.stripe_subscription_id,
                message="Stripe subscription cancellation will be implemented in billing module",
            )

        # TODO: Archive user data when data archival is implemented
        logger.debug(
            "user_data_archival_placeholder",
            user_id=str(user.id),
            message="User data archival will be implemented for compliance",
        )

    async def on_after_delete(
        self,
        user: User,
        request: Request | None = None,
    ) -> None:
        """Handle post-deletion tasks."""
        logger.info(
            "user_deleted",
            user_id=str(user.id),
            email=user.email,
        )

    # ==========================================================================
    # Custom JWT Claims
    # ==========================================================================

    async def on_after_update(
        self,
        user: User,
        update_dict: dict[str, Any],
        request: Request | None = None,
    ) -> None:
        """Handle post-update tasks."""
        logger.info(
            "user_updated",
            user_id=str(user.id),
            updated_fields=list(update_dict.keys()),
        )
