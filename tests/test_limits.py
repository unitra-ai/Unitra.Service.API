"""Tests for tier limits configuration."""

import pytest

from app.core.limits import TIER_LIMITS, Tier, get_tier_limits


class TestTierLimits:
    """Tests for tier limits configuration."""

    def test_tier_enum_values(self) -> None:
        """Test Tier enum has expected values."""
        assert Tier.FREE.value == "free"
        assert Tier.BASIC.value == "basic"
        assert Tier.PRO.value == "pro"
        assert Tier.ENTERPRISE.value == "enterprise"

    def test_free_tier_limits(self) -> None:
        """Test FREE tier has expected limits."""
        limits = TIER_LIMITS[Tier.FREE]
        assert limits.tokens_per_week == 10_000
        assert limits.requests_per_minute == 20
        assert limits.cloud_mt_allowed is False
        assert limits.priority_support is False

    def test_basic_tier_limits(self) -> None:
        """Test BASIC tier has expected limits."""
        limits = TIER_LIMITS[Tier.BASIC]
        assert limits.tokens_per_week == 100_000
        assert limits.requests_per_minute == 60
        assert limits.cloud_mt_allowed is True
        assert limits.priority_support is False

    def test_pro_tier_limits(self) -> None:
        """Test PRO tier has expected limits."""
        limits = TIER_LIMITS[Tier.PRO]
        assert limits.tokens_per_week == 500_000
        assert limits.requests_per_minute == 120
        assert limits.cloud_mt_allowed is True
        assert limits.priority_support is True

    def test_enterprise_tier_limits(self) -> None:
        """Test ENTERPRISE tier has expected limits."""
        limits = TIER_LIMITS[Tier.ENTERPRISE]
        assert limits.tokens_per_week == 5_000_000
        assert limits.requests_per_minute == 300
        assert limits.cloud_mt_allowed is True
        assert limits.priority_support is True

    def test_get_tier_limits_with_enum(self) -> None:
        """Test get_tier_limits with Tier enum."""
        limits = get_tier_limits(Tier.PRO)
        assert limits.tokens_per_week == 500_000

    def test_get_tier_limits_with_string(self) -> None:
        """Test get_tier_limits with string value."""
        limits = get_tier_limits("pro")
        assert limits.tokens_per_week == 500_000

    def test_get_tier_limits_with_invalid_string(self) -> None:
        """Test get_tier_limits returns FREE for invalid string."""
        limits = get_tier_limits("invalid")
        assert limits.tokens_per_week == 10_000
        assert limits.cloud_mt_allowed is False

    def test_tier_limits_immutable(self) -> None:
        """Test TierLimits is immutable (frozen dataclass)."""
        limits = TIER_LIMITS[Tier.FREE]
        # Frozen dataclasses raise FrozenInstanceError (subclass of AttributeError)
        with pytest.raises(AttributeError):
            limits.tokens_per_week = 999  # type: ignore
