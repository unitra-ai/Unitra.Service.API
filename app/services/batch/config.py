"""Tier-based batch configuration.

Design principles:
1. Higher tier = higher priority (processed first)
2. Higher tier = smaller max_batch (lower latency)
3. Higher tier = shorter max_wait (faster response)
4. All tiers benefit from batching (even Free is faster than no-batch)

Performance targets from cost model:
- Free:       150-250ms total latency
- Basic:      120-200ms total latency
- Pro:        100-170ms total latency
- Enterprise: 80-140ms total latency
"""

from dataclasses import dataclass
from enum import Enum


class UserTier(str, Enum):
    """User subscription tiers."""

    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    def __str__(self) -> str:
        """Return the tier value as string."""
        return self.value


@dataclass(frozen=True)
class TierConfig:
    """Configuration for a specific tier's batch processing."""

    priority: int  # Base priority (higher = more important)
    max_batch_size: int  # Maximum batch size for this tier
    min_batch_size: int  # Minimum batch before processing
    max_wait_ms: int  # Maximum queue wait time in milliseconds
    target_latency_ms: int  # Target total latency (for monitoring)


# Tier configurations optimized for cost/latency tradeoffs
TIER_CONFIGS: dict[UserTier, TierConfig] = {
    UserTier.FREE: TierConfig(
        priority=1,
        max_batch_size=32,
        min_batch_size=8,
        max_wait_ms=100,
        target_latency_ms=200,
    ),
    UserTier.BASIC: TierConfig(
        priority=2,
        max_batch_size=16,
        min_batch_size=4,
        max_wait_ms=60,
        target_latency_ms=160,
    ),
    UserTier.PRO: TierConfig(
        priority=3,
        max_batch_size=12,
        min_batch_size=4,
        max_wait_ms=40,
        target_latency_ms=135,
    ),
    UserTier.ENTERPRISE: TierConfig(
        priority=4,
        max_batch_size=8,
        min_batch_size=2,
        max_wait_ms=20,
        target_latency_ms=110,
    ),
}


def get_tier_config(tier: UserTier) -> TierConfig:
    """Get configuration for a specific tier."""
    return TIER_CONFIGS[tier]


def tier_from_string(tier_str: str) -> UserTier:
    """Convert string to UserTier, defaulting to FREE."""
    try:
        return UserTier(tier_str.lower())
    except ValueError:
        return UserTier.FREE
