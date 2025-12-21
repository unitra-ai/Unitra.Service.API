"""Tests for database models."""

import uuid
from datetime import datetime, timezone

import pytest

from app.models import (
    ProcessingLocation,
    RefreshToken,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    UsageLog,
    User,
    UserTier,
)


class TestUserModel:
    """Tests for User model."""

    def test_user_tier_enum_values(self) -> None:
        """Test UserTier enum has expected values."""
        assert UserTier.FREE.value == "free"
        assert UserTier.BASIC.value == "basic"
        assert UserTier.PRO.value == "pro"
        assert UserTier.ENTERPRISE.value == "enterprise"

    def test_user_default_tier(self) -> None:
        """Test User model has FREE as default tier."""
        assert User.tier.default.arg == UserTier.FREE

    def test_user_default_is_active(self) -> None:
        """Test User model has is_active default to True."""
        assert User.is_active.default.arg is True

    def test_user_default_is_verified(self) -> None:
        """Test User model has is_verified default to False."""
        assert User.is_verified.default.arg is False


class TestSubscriptionModel:
    """Tests for Subscription model."""

    def test_subscription_status_enum_values(self) -> None:
        """Test SubscriptionStatus enum has expected values."""
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.CANCELED.value == "canceled"
        assert SubscriptionStatus.PAST_DUE.value == "past_due"
        assert SubscriptionStatus.UNPAID.value == "unpaid"
        assert SubscriptionStatus.TRIALING.value == "trialing"

    def test_subscription_plan_enum_values(self) -> None:
        """Test SubscriptionPlan enum has expected values."""
        assert SubscriptionPlan.BASIC_MONTHLY.value == "basic_monthly"
        assert SubscriptionPlan.BASIC_YEARLY.value == "basic_yearly"
        assert SubscriptionPlan.PRO_MONTHLY.value == "pro_monthly"
        assert SubscriptionPlan.PRO_YEARLY.value == "pro_yearly"


class TestUsageLogModel:
    """Tests for UsageLog model."""

    def test_processing_location_enum_values(self) -> None:
        """Test ProcessingLocation enum has expected values."""
        assert ProcessingLocation.LOCAL.value == "local"
        assert ProcessingLocation.CLOUD.value == "cloud"


class TestRefreshTokenModel:
    """Tests for RefreshToken model."""

    def test_refresh_token_default_revoked(self) -> None:
        """Test RefreshToken model has revoked default to False."""
        assert RefreshToken.revoked.default.arg is False
