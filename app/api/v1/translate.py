"""Translation endpoints.

This module provides the translation API endpoints that integrate with
the Modal-hosted ML service for machine translation.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_user
from app.auth.models import User
from app.core.exceptions import (
    InsufficientTierError,
    InvalidLanguageError,
    RateLimitError,
    UsageLimitExceededError,
)
from app.core.limits import Tier, get_tier_limits
from app.db.redis import RedisClient, get_redis_client
from app.db.session import get_db_session
from app.models.usage import ProcessingLocation, UsageLog
from app.services.mt_client import MTClient

logger = structlog.get_logger(__name__)

router = APIRouter()


# =============================================================================
# Supported Languages
# =============================================================================

# Priority languages (high-quality, well-tested)
PRIORITY_LANGUAGES = {
    "en": "English",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
}

# Extended language support (MADLAD-400 supports 400+ languages)
EXTENDED_LANGUAGES = {
    "it": "Italian",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "uk": "Ukrainian",
    "cs": "Czech",
    "ro": "Romanian",
    "hu": "Hungarian",
    "el": "Greek",
    "he": "Hebrew",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
}

# All supported languages
SUPPORTED_LANGUAGES = {**PRIORITY_LANGUAGES, **EXTENDED_LANGUAGES}

# Language code aliases
LANGUAGE_ALIASES = {
    "zh-cn": "zh",
    "zh-hans": "zh",
    "zh-tw": "zh",  # Map to simplified for now
    "zh-hant": "zh",
    "pt-br": "pt",
    "pt-pt": "pt",
}


def normalize_language(code: str) -> str:
    """Normalize and validate a language code.

    Args:
        code: Raw language code

    Returns:
        Normalized language code

    Raises:
        InvalidLanguageError: If language is not supported
    """
    normalized = code.lower().strip()

    # Check aliases first
    if normalized in LANGUAGE_ALIASES:
        normalized = LANGUAGE_ALIASES[normalized]

    # Validate against supported languages
    if normalized not in SUPPORTED_LANGUAGES:
        raise InvalidLanguageError(code)

    return normalized


# =============================================================================
# Request/Response Models
# =============================================================================


class TranslateRequest(BaseModel):
    """Translation request body."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Text to translate (max 512 characters)",
    )
    source_lang: str = Field(
        default="en",
        description="Source language code (e.g., 'en', 'zh')",
    )
    target_lang: str = Field(
        ...,
        description="Target language code (e.g., 'zh', 'ja')",
    )


class TranslateResponse(BaseModel):
    """Translation response."""

    translated_text: str
    source_lang: str
    target_lang: str
    tokens_used: int
    latency_ms: float
    processing_mode: str = "cloud"


class BatchTranslateRequest(BaseModel):
    """Batch translation request."""

    texts: list[str] = Field(
        ...,
        min_length=1,
        max_length=16,
        description="List of texts to translate (max 16 texts)",
    )
    source_lang: str = Field(
        default="en",
        description="Source language code",
    )
    target_lang: str = Field(
        ...,
        description="Target language code",
    )


class BatchTranslateResponse(BaseModel):
    """Batch translation response."""

    translations: list[str]
    source_lang: str
    target_lang: str
    total_tokens: int
    total_latency_ms: float
    processing_mode: str = "cloud"


class UsageResponse(BaseModel):
    """Usage information response."""

    tokens_used_this_week: int
    tokens_limit: int
    tokens_remaining: int
    requests_per_minute_limit: int


# =============================================================================
# Dependencies
# =============================================================================

CurrentUser = Annotated[User, Depends(current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Redis = Annotated[RedisClient, Depends(get_redis_client)]


# =============================================================================
# Helper Functions
# =============================================================================


async def check_usage_limits(
    user: User,
    redis: RedisClient,
    tokens_estimate: int = 100,
) -> tuple[int, int]:
    """Check if user has sufficient quota and rate limit capacity.

    Args:
        user: Current user
        redis: Redis client
        tokens_estimate: Estimated tokens for this request

    Returns:
        Tuple of (current_usage, limit)

    Raises:
        InsufficientTierError: If user tier doesn't allow cloud MT
        UsageLimitExceededError: If weekly quota exceeded
        RateLimitError: If rate limit exceeded
    """
    tier = Tier(user.tier)
    limits = get_tier_limits(tier)

    # Check if cloud MT is allowed for this tier
    if not limits.cloud_mt_allowed:
        raise InsufficientTierError("BASIC")

    # Check rate limit
    allowed, remaining = await redis.check_rate_limit(
        user_id=str(user.id),
        endpoint="translate",
        limit=limits.requests_per_minute,
        window=60,
    )
    if not allowed:
        ttl = await redis.get_rate_limit_ttl(str(user.id), "translate")
        raise RateLimitError(retry_after=max(ttl, 1))

    # Check weekly usage quota
    current_usage = await redis.get_usage(str(user.id))
    if current_usage + tokens_estimate > limits.tokens_per_week:
        raise UsageLimitExceededError(
            limit=limits.tokens_per_week,
            used=current_usage,
        )

    return current_usage, limits.tokens_per_week


async def record_usage(
    user_id: str,
    tokens: int,
    source_lang: str,
    target_lang: str,
    redis: RedisClient,
    db: AsyncSession,
) -> None:
    """Record usage to Redis and database.

    Args:
        user_id: User UUID string
        tokens: Tokens used
        source_lang: Source language code
        target_lang: Target language code
        redis: Redis client
        db: Database session
    """
    # Update Redis counter (fast path)
    await redis.increment_usage(user_id, tokens)

    # Record to database (durable storage)
    usage_log = UsageLog(
        user_id=user_id,
        tokens_used=tokens,
        source_lang=source_lang,
        target_lang=target_lang,
        processing_location=ProcessingLocation.CLOUD,
    )
    db.add(usage_log)
    await db.commit()


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=TranslateResponse)
async def translate(
    request: TranslateRequest,
    user: CurrentUser,
    db: DbSession,
    redis: Redis,
) -> TranslateResponse:
    """Translate text using the cloud MT service.

    Requires authentication. Usage is tracked against weekly quota.

    - FREE tier: No cloud MT access
    - BASIC tier: 100K tokens/week, 60 req/min
    - PRO tier: 500K tokens/week, 120 req/min
    - ENTERPRISE tier: 5M tokens/week, 300 req/min
    """
    # Normalize language codes
    source_lang = normalize_language(request.source_lang)
    target_lang = normalize_language(request.target_lang)

    # Validate different languages
    if source_lang == target_lang:
        raise InvalidLanguageError(f"Source and target languages must be different: {source_lang}")

    # Estimate tokens (rough: 1 token per 4 characters)
    tokens_estimate = max(len(request.text) // 4, 10)

    # Check usage limits
    await check_usage_limits(user, redis, tokens_estimate)

    logger.info(
        "translate_request",
        user_id=str(user.id),
        source_lang=source_lang,
        target_lang=target_lang,
        text_length=len(request.text),
    )

    # Call Modal MT service
    async with MTClient() as mt_client:
        result = await mt_client.translate(
            text=request.text,
            source_lang=source_lang,
            target_lang=target_lang,
        )

    # Record usage
    await record_usage(
        user_id=str(user.id),
        tokens=result.tokens_used,
        source_lang=source_lang,
        target_lang=target_lang,
        redis=redis,
        db=db,
    )

    logger.info(
        "translate_success",
        user_id=str(user.id),
        tokens_used=result.tokens_used,
        latency_ms=result.latency_ms,
    )

    return TranslateResponse(
        translated_text=result.translation,
        source_lang=source_lang,
        target_lang=target_lang,
        tokens_used=result.tokens_used,
        latency_ms=result.latency_ms,
        processing_mode=result.processing_mode,
    )


@router.post("/batch", response_model=BatchTranslateResponse)
async def translate_batch(
    request: BatchTranslateRequest,
    user: CurrentUser,
    db: DbSession,
    redis: Redis,
) -> BatchTranslateResponse:
    """Translate multiple texts in a batch.

    More efficient than individual requests for multiple texts.
    Maximum 16 texts per batch.

    Requires authentication. Usage is tracked against weekly quota.
    """
    # Validate batch size
    if len(request.texts) > 16:
        raise InvalidLanguageError("Maximum 16 texts per batch")

    # Validate text lengths
    for i, text in enumerate(request.texts):
        if len(text) > 512:
            raise InvalidLanguageError(f"Text {i} exceeds 512 character limit")
        if not text.strip():
            raise InvalidLanguageError(f"Text {i} is empty")

    # Normalize language codes
    source_lang = normalize_language(request.source_lang)
    target_lang = normalize_language(request.target_lang)

    if source_lang == target_lang:
        raise InvalidLanguageError(f"Source and target languages must be different: {source_lang}")

    # Estimate total tokens
    total_chars = sum(len(t) for t in request.texts)
    tokens_estimate = max(total_chars // 4, 10 * len(request.texts))

    # Check usage limits
    await check_usage_limits(user, redis, tokens_estimate)

    logger.info(
        "translate_batch_request",
        user_id=str(user.id),
        source_lang=source_lang,
        target_lang=target_lang,
        batch_size=len(request.texts),
    )

    # Call Modal MT service
    async with MTClient() as mt_client:
        result = await mt_client.translate_batch(
            texts=request.texts,
            source_lang=source_lang,
            target_lang=target_lang,
        )

    # Record usage
    await record_usage(
        user_id=str(user.id),
        tokens=result.total_tokens,
        source_lang=source_lang,
        target_lang=target_lang,
        redis=redis,
        db=db,
    )

    logger.info(
        "translate_batch_success",
        user_id=str(user.id),
        total_tokens=result.total_tokens,
        latency_ms=result.latency_ms,
        batch_size=len(result.translations),
    )

    return BatchTranslateResponse(
        translations=result.translations,
        source_lang=source_lang,
        target_lang=target_lang,
        total_tokens=result.total_tokens,
        total_latency_ms=result.latency_ms,
        processing_mode=result.processing_mode,
    )


class LanguageInfo(BaseModel):
    """Language information."""

    code: str
    name: str
    priority: bool


class LanguagesResponse(BaseModel):
    """Languages list response."""

    priority_languages: list[LanguageInfo]
    extended_languages: list[LanguageInfo]
    total_supported: int


@router.get("/languages", response_model=LanguagesResponse)
async def list_languages() -> LanguagesResponse:
    """List supported languages.

    Returns priority languages (high-quality, well-tested) and
    extended languages (additional MADLAD-400 support).
    """
    priority = [
        LanguageInfo(code=code, name=name, priority=True)
        for code, name in PRIORITY_LANGUAGES.items()
    ]
    extended = [
        LanguageInfo(code=code, name=name, priority=False)
        for code, name in EXTENDED_LANGUAGES.items()
    ]

    return LanguagesResponse(
        priority_languages=priority,
        extended_languages=extended,
        total_supported=len(SUPPORTED_LANGUAGES),
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user: CurrentUser,
    redis: Redis,
) -> UsageResponse:
    """Get current usage statistics for the authenticated user.

    Returns tokens used this week, remaining quota, and rate limits.
    """
    tier = Tier(user.tier)
    limits = get_tier_limits(tier)

    tokens_used = await redis.get_usage(str(user.id))
    tokens_remaining = max(0, limits.tokens_per_week - tokens_used)

    return UsageResponse(
        tokens_used_this_week=tokens_used,
        tokens_limit=limits.tokens_per_week,
        tokens_remaining=tokens_remaining,
        requests_per_minute_limit=limits.requests_per_minute,
    )
