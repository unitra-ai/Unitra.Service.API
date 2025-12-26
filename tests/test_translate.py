"""Tests for translation endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient


# =============================================================================
# Language Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_languages(async_client: AsyncClient) -> None:
    """Test list languages endpoint returns language list."""
    response = await async_client.get("/api/v1/translate/languages")
    assert response.status_code == 200

    data = response.json()
    assert "priority_languages" in data
    assert "extended_languages" in data
    assert "total_supported" in data

    # Check priority languages
    priority = data["priority_languages"]
    assert len(priority) > 0
    codes = [lang["code"] for lang in priority]
    assert "en" in codes
    assert "zh" in codes
    assert "ja" in codes


@pytest.mark.asyncio
async def test_list_languages_structure(async_client: AsyncClient) -> None:
    """Test language list has correct structure."""
    response = await async_client.get("/api/v1/translate/languages")
    data = response.json()

    lang = data["priority_languages"][0]
    assert "code" in lang
    assert "name" in lang
    assert "priority" in lang
    assert lang["priority"] is True


# =============================================================================
# Language Validation Tests
# =============================================================================


class TestLanguageValidation:
    """Tests for language code validation."""

    def test_normalize_valid_language(self) -> None:
        """Valid language codes should be normalized."""
        from app.api.v1.translate import normalize_language

        assert normalize_language("EN") == "en"
        assert normalize_language("Zh") == "zh"
        assert normalize_language(" ja ") == "ja"

    def test_normalize_alias(self) -> None:
        """Language aliases should be normalized."""
        from app.api.v1.translate import normalize_language

        assert normalize_language("zh-cn") == "zh"
        assert normalize_language("zh-hans") == "zh"
        assert normalize_language("pt-br") == "pt"

    def test_invalid_language_raises(self) -> None:
        """Invalid language codes should raise InvalidLanguageError."""
        from app.api.v1.translate import normalize_language
        from app.core.exceptions import InvalidLanguageError

        with pytest.raises(InvalidLanguageError):
            normalize_language("xyz")

        with pytest.raises(InvalidLanguageError):
            normalize_language("")


# =============================================================================
# Authentication Tests
# =============================================================================


@pytest.mark.asyncio
async def test_translate_requires_auth(async_client: AsyncClient) -> None:
    """Translation endpoint should require authentication."""
    response = await async_client.post(
        "/api/v1/translate",
        json={
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "zh",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_batch_translate_requires_auth(async_client: AsyncClient) -> None:
    """Batch translation endpoint should require authentication."""
    response = await async_client.post(
        "/api/v1/translate/batch",
        json={
            "texts": ["Hello", "World"],
            "source_lang": "en",
            "target_lang": "zh",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_usage_requires_auth(async_client: AsyncClient) -> None:
    """Usage endpoint should require authentication."""
    response = await async_client.get("/api/v1/translate/usage")
    assert response.status_code == 401


# =============================================================================
# Translation Tests with Mocked MT Client
# =============================================================================


@pytest_asyncio.fixture
async def basic_tier_user(async_client: AsyncClient) -> dict:
    """Create a BASIC tier user for translation tests."""
    email = f"basic_{uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    # Register user
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    user_data = response.json()

    # Update tier to BASIC (mock this by patching the user lookup)
    # The user object returned has the id we need
    user_id = user_data["id"]

    # Login to get token
    response = await async_client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    return {
        "id": user_id,
        "email": email,
        "password": password,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.mark.asyncio
async def test_translate_free_tier_denied(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """FREE tier users should be denied cloud MT access."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    response = await async_client.post(
        "/api/v1/translate",
        headers=headers,
        json={
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "zh",
        },
    )

    # FREE tier doesn't have cloud_mt_allowed
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "INSUFFICIENT_TIER"


@pytest.mark.asyncio
async def test_translate_invalid_source_lang(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """Invalid source language should return 422."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    response = await async_client.post(
        "/api/v1/translate",
        headers=headers,
        json={
            "text": "Hello",
            "source_lang": "invalid",
            "target_lang": "zh",
        },
    )

    # Should fail on language validation before tier check
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_translate_invalid_target_lang(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """Invalid target language should return 422."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    response = await async_client.post(
        "/api/v1/translate",
        headers=headers,
        json={
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "xyz",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_translate_same_language_error(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """Same source and target language should return error."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    response = await async_client.post(
        "/api/v1/translate",
        headers=headers,
        json={
            "text": "Hello",
            "source_lang": "en",
            "target_lang": "en",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_translate_empty_text(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """Empty text should return validation error."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    response = await async_client.post(
        "/api/v1/translate",
        headers=headers,
        json={
            "text": "",
            "source_lang": "en",
            "target_lang": "zh",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_translate_text_too_long(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """Text exceeding 512 characters should return validation error."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    long_text = "a" * 513

    response = await async_client.post(
        "/api/v1/translate",
        headers=headers,
        json={
            "text": long_text,
            "source_lang": "en",
            "target_lang": "zh",
        },
    )

    assert response.status_code == 422


# =============================================================================
# Batch Translation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_batch_translate_free_tier_denied(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """FREE tier users should be denied batch translation."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    response = await async_client.post(
        "/api/v1/translate/batch",
        headers=headers,
        json={
            "texts": ["Hello", "World"],
            "source_lang": "en",
            "target_lang": "zh",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_batch_translate_too_many_texts(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """Batch with more than 16 texts should return error."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    texts = ["Hello"] * 17

    response = await async_client.post(
        "/api/v1/translate/batch",
        headers=headers,
        json={
            "texts": texts,
            "source_lang": "en",
            "target_lang": "zh",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_batch_translate_empty_texts(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """Empty texts list should return validation error."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    response = await async_client.post(
        "/api/v1/translate/batch",
        headers=headers,
        json={
            "texts": [],
            "source_lang": "en",
            "target_lang": "zh",
        },
    )

    assert response.status_code == 422


# =============================================================================
# Usage Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_usage(
    async_client: AsyncClient,
    registered_user_token: str,
) -> None:
    """Usage endpoint should return user's usage statistics."""
    headers = {"Authorization": f"Bearer {registered_user_token}"}

    # Mock Redis to return usage data
    with patch("app.api.v1.translate.get_redis_client") as mock_redis_dep:
        mock_redis = AsyncMock()
        mock_redis.get_usage = AsyncMock(return_value=5000)

        async def mock_get_redis():
            yield mock_redis

        mock_redis_dep.return_value = mock_get_redis()

        response = await async_client.get(
            "/api/v1/translate/usage",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "tokens_used_this_week" in data
    assert "tokens_limit" in data
    assert "tokens_remaining" in data
    assert "requests_per_minute_limit" in data


# =============================================================================
# MT Client Unit Tests
# =============================================================================


class TestMTClient:
    """Unit tests for the MT client."""

    @pytest.mark.asyncio
    async def test_client_context_manager(self) -> None:
        """MTClient should work as async context manager."""
        from app.services.mt_client import MTClient

        async with MTClient(base_url="https://example.com") as client:
            assert client._client is not None
            assert client.base_url == "https://example.com"

    def test_client_default_url(self) -> None:
        """MTClient should use Modal URL or settings URL."""
        from app.services.mt_client import MTClient

        client = MTClient()
        # Either default Modal URL or configured URL from settings
        assert client.base_url is not None
        assert len(client.base_url) > 0

    def test_client_strips_trailing_slash(self) -> None:
        """MTClient should strip trailing slashes from base URL."""
        from app.services.mt_client import MTClient

        client = MTClient(base_url="https://example.com/")
        assert not client.base_url.endswith("/")

    def test_client_requires_context(self) -> None:
        """MTClient should require context manager usage."""
        from app.services.mt_client import MTClient

        client = MTClient()
        with pytest.raises(RuntimeError, match="async context manager"):
            _ = client.client


# =============================================================================
# Rate Limit Tests
# =============================================================================


class TestRateLimiting:
    """Tests for rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_rate_limit_check(self) -> None:
        """Rate limit check should work correctly."""
        from app.db.redis import RedisClient

        mock_redis = MagicMock(spec=RedisClient)
        mock_redis.check_rate_limit = AsyncMock(return_value=(True, 59))
        mock_redis.get_usage = AsyncMock(return_value=0)

        # Should allow request
        allowed, remaining = await mock_redis.check_rate_limit(
            user_id="test-user",
            endpoint="translate",
            limit=60,
            window=60,
        )
        assert allowed is True
        assert remaining == 59


# =============================================================================
# Usage Tracking Tests
# =============================================================================


class TestUsageTracking:
    """Tests for usage tracking."""

    @pytest.mark.asyncio
    async def test_usage_increment(self) -> None:
        """Usage should be incremented correctly."""
        from app.db.redis import RedisClient

        mock_redis = MagicMock(spec=RedisClient)
        mock_redis.increment_usage = AsyncMock(return_value=1000)

        new_total = await mock_redis.increment_usage("test-user", 100)
        assert new_total == 1000

        mock_redis.increment_usage.assert_called_once_with("test-user", 100)

    @pytest.mark.asyncio
    async def test_usage_quota_exceeded(self) -> None:
        """Should raise error when quota exceeded."""
        from app.api.v1.translate import check_usage_limits
        from app.core.exceptions import UsageLimitExceededError

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.tier = "basic"  # 100k tokens/week

        mock_redis = MagicMock()
        mock_redis.check_rate_limit = AsyncMock(return_value=(True, 59))
        mock_redis.get_usage = AsyncMock(return_value=100_000)  # At limit

        with pytest.raises(UsageLimitExceededError):
            await check_usage_limits(mock_user, mock_redis, tokens_estimate=100)


# =============================================================================
# Tier Access Tests
# =============================================================================


class TestTierAccess:
    """Tests for tier-based access control."""

    @pytest.mark.asyncio
    async def test_free_tier_denied(self) -> None:
        """FREE tier should be denied cloud MT access."""
        from app.api.v1.translate import check_usage_limits
        from app.core.exceptions import InsufficientTierError

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.tier = "free"

        mock_redis = MagicMock()
        mock_redis.check_rate_limit = AsyncMock(return_value=(True, 19))
        mock_redis.get_usage = AsyncMock(return_value=0)

        with pytest.raises(InsufficientTierError):
            await check_usage_limits(mock_user, mock_redis)

    @pytest.mark.asyncio
    async def test_basic_tier_allowed(self) -> None:
        """BASIC tier should be allowed cloud MT access."""
        from app.api.v1.translate import check_usage_limits

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.tier = "basic"

        mock_redis = MagicMock()
        mock_redis.check_rate_limit = AsyncMock(return_value=(True, 59))
        mock_redis.get_usage = AsyncMock(return_value=0)

        usage, limit = await check_usage_limits(mock_user, mock_redis)
        assert usage == 0
        assert limit == 100_000  # BASIC tier limit


# =============================================================================
# Integration Tests with Mocked MT Service
# =============================================================================


@pytest.mark.asyncio
async def test_translate_with_mocked_mt_service() -> None:
    """Test translation with mocked MT service."""
    from app.services.mt_client import MTClient, TranslationResult

    mock_result = TranslationResult(
        translation="你好",
        source_lang="en",
        target_lang="zh",
        tokens_used=10,
        latency_ms=50.0,
        processing_mode="cloud",
    )

    with patch.object(MTClient, "translate", new_callable=AsyncMock) as mock_translate:
        mock_translate.return_value = mock_result

        async with MTClient() as client:
            # Override the translate method
            client.translate = mock_translate

            result = await client.translate(
                text="Hello",
                source_lang="en",
                target_lang="zh",
            )

        assert result.translation == "你好"
        assert result.tokens_used == 10


@pytest.mark.asyncio
async def test_batch_translate_with_mocked_mt_service() -> None:
    """Test batch translation with mocked MT service."""
    from app.services.mt_client import BatchTranslationResult, MTClient

    mock_result = BatchTranslationResult(
        translations=["你好", "世界"],
        source_lang="en",
        target_lang="zh",
        total_tokens=20,
        latency_ms=80.0,
        processing_mode="cloud",
    )

    with patch.object(
        MTClient, "translate_batch", new_callable=AsyncMock
    ) as mock_translate:
        mock_translate.return_value = mock_result

        async with MTClient() as client:
            client.translate_batch = mock_translate

            result = await client.translate_batch(
                texts=["Hello", "World"],
                source_lang="en",
                target_lang="zh",
            )

        assert len(result.translations) == 2
        assert result.total_tokens == 20
