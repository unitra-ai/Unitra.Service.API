"""Usage tracking endpoints."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class UsageSummary(BaseModel):
    """Usage summary for a period."""

    period: str  # "day", "week", "month"
    start_date: datetime
    end_date: datetime
    total_characters: int
    total_requests: int
    languages_used: list[str]


class UsageDetail(BaseModel):
    """Detailed usage record."""

    timestamp: datetime
    source_lang: str
    target_lang: str
    character_count: int
    latency_ms: float


class UsageResponse(BaseModel):
    """Usage response with summary and optional details."""

    summary: UsageSummary
    details: list[UsageDetail] | None = None


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    period: Literal["day", "week", "month"] = "month",
    include_details: bool = False,
) -> UsageResponse:
    """Get usage statistics.

    TODO: Implement actual usage tracking from database.
    """
    raise HTTPException(status_code=501, detail="Usage tracking not yet implemented.")


@router.get("/usage/quota")
async def get_quota() -> dict[str, int | str]:
    """Get current quota status.

    TODO: Implement quota checking based on subscription tier.
    """
    raise HTTPException(status_code=501, detail="Quota system not yet implemented.")
