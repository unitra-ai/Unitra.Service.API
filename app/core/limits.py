"""Tier limits configuration."""

from dataclasses import dataclass
from enum import Enum


class Tier(str, Enum):
    """User tier levels."""

    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class TierLimits:
    """Limits for a specific tier."""

    tokens_per_week: int
    requests_per_minute: int
    cloud_mt_allowed: bool
    priority_support: bool


TIER_LIMITS: dict[Tier, TierLimits] = {
    Tier.FREE: TierLimits(
        tokens_per_week=10_000,
        requests_per_minute=20,
        cloud_mt_allowed=False,
        priority_support=False,
    ),
    Tier.BASIC: TierLimits(
        tokens_per_week=100_000,
        requests_per_minute=60,
        cloud_mt_allowed=True,
        priority_support=False,
    ),
    Tier.PRO: TierLimits(
        tokens_per_week=500_000,
        requests_per_minute=120,
        cloud_mt_allowed=True,
        priority_support=True,
    ),
    Tier.ENTERPRISE: TierLimits(
        tokens_per_week=5_000_000,
        requests_per_minute=300,
        cloud_mt_allowed=True,
        priority_support=True,
    ),
}


def get_tier_limits(tier: Tier | str) -> TierLimits:
    """Get limits for a specific tier.

    Args:
        tier: Tier enum or string value

    Returns:
        TierLimits for the given tier, defaults to FREE if invalid
    """
    if isinstance(tier, str):
        try:
            tier = Tier(tier)
        except ValueError:
            tier = Tier.FREE

    return TIER_LIMITS.get(tier, TIER_LIMITS[Tier.FREE])
