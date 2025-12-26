"""Test tier configuration.

Test cases:
1. Tier priority ordering
2. Config values are valid
3. Tier string conversion
"""

import pytest

from app.services.batch.config import (
    TIER_CONFIGS,
    TierConfig,
    UserTier,
    get_tier_config,
    tier_from_string,
)


class TestTierPriority:
    """Test tier priority ordering."""

    def test_priority_ordering(self) -> None:
        """Enterprise should have highest priority."""
        assert TIER_CONFIGS[UserTier.ENTERPRISE].priority > TIER_CONFIGS[UserTier.PRO].priority
        assert TIER_CONFIGS[UserTier.PRO].priority > TIER_CONFIGS[UserTier.BASIC].priority
        assert TIER_CONFIGS[UserTier.BASIC].priority > TIER_CONFIGS[UserTier.FREE].priority

    def test_all_tiers_have_config(self) -> None:
        """All tiers should have configuration."""
        for tier in UserTier:
            assert tier in TIER_CONFIGS
            config = TIER_CONFIGS[tier]
            assert isinstance(config, TierConfig)


class TestConfigValues:
    """Test configuration value constraints."""

    def test_batch_sizes_valid(self) -> None:
        """Batch sizes should be valid."""
        for tier, config in TIER_CONFIGS.items():
            assert config.min_batch_size > 0
            assert config.max_batch_size >= config.min_batch_size
            assert config.max_batch_size <= 64  # Reasonable upper limit

    def test_wait_times_valid(self) -> None:
        """Wait times should be positive and reasonable."""
        for tier, config in TIER_CONFIGS.items():
            assert config.max_wait_ms > 0
            assert config.max_wait_ms <= 1000  # Max 1 second

    def test_target_latency_valid(self) -> None:
        """Target latencies should be positive and reasonable."""
        for tier, config in TIER_CONFIGS.items():
            assert config.target_latency_ms > 0
            assert config.target_latency_ms <= 500  # Max 500ms

    def test_higher_tier_lower_latency(self) -> None:
        """Higher tiers should have lower target latency."""
        assert (
            TIER_CONFIGS[UserTier.ENTERPRISE].target_latency_ms
            < TIER_CONFIGS[UserTier.PRO].target_latency_ms
        )
        assert (
            TIER_CONFIGS[UserTier.PRO].target_latency_ms
            < TIER_CONFIGS[UserTier.BASIC].target_latency_ms
        )
        assert (
            TIER_CONFIGS[UserTier.BASIC].target_latency_ms
            < TIER_CONFIGS[UserTier.FREE].target_latency_ms
        )

    def test_higher_tier_smaller_batch(self) -> None:
        """Higher tiers should have smaller max batch (lower latency)."""
        assert (
            TIER_CONFIGS[UserTier.ENTERPRISE].max_batch_size
            <= TIER_CONFIGS[UserTier.PRO].max_batch_size
        )
        assert (
            TIER_CONFIGS[UserTier.PRO].max_batch_size
            <= TIER_CONFIGS[UserTier.BASIC].max_batch_size
        )
        assert (
            TIER_CONFIGS[UserTier.BASIC].max_batch_size
            <= TIER_CONFIGS[UserTier.FREE].max_batch_size
        )


class TestTierHelpers:
    """Test helper functions."""

    def test_get_tier_config(self) -> None:
        """get_tier_config should return correct config."""
        config = get_tier_config(UserTier.PRO)
        assert config == TIER_CONFIGS[UserTier.PRO]
        assert config.priority == 3

    def test_tier_from_string_valid(self) -> None:
        """tier_from_string should convert valid strings."""
        assert tier_from_string("free") == UserTier.FREE
        assert tier_from_string("basic") == UserTier.BASIC
        assert tier_from_string("pro") == UserTier.PRO
        assert tier_from_string("enterprise") == UserTier.ENTERPRISE

    def test_tier_from_string_case_insensitive(self) -> None:
        """tier_from_string should be case insensitive."""
        assert tier_from_string("FREE") == UserTier.FREE
        assert tier_from_string("Basic") == UserTier.BASIC
        assert tier_from_string("PRO") == UserTier.PRO
        assert tier_from_string("ENTERPRISE") == UserTier.ENTERPRISE

    def test_tier_from_string_invalid(self) -> None:
        """tier_from_string should default to FREE for invalid strings."""
        assert tier_from_string("invalid") == UserTier.FREE
        assert tier_from_string("premium") == UserTier.FREE
        assert tier_from_string("") == UserTier.FREE


class TestTierEnum:
    """Test UserTier enum."""

    def test_tier_values(self) -> None:
        """Tier values should be lowercase strings."""
        assert UserTier.FREE.value == "free"
        assert UserTier.BASIC.value == "basic"
        assert UserTier.PRO.value == "pro"
        assert UserTier.ENTERPRISE.value == "enterprise"

    def test_tier_str(self) -> None:
        """Tier should be usable as string."""
        assert str(UserTier.FREE) == "free"
        assert f"{UserTier.PRO}" == "pro"
