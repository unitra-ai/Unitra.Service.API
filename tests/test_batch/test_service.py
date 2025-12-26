"""End-to-end service integration tests.

Test cases:
1. Full translation flow
2. Concurrent users
3. Tier differentiation
4. Error recovery
5. Service lifecycle
6. Metrics accuracy
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services.batch import (
    BatchTranslationService,
    UserTier,
)


@pytest.fixture
def mock_modal_response():
    """Mock Modal service response."""

    async def mock_post(url: str, json: dict):
        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                if "texts" in json:
                    return {
                        "translations": [f"translated_{t}" for t in json["texts"]],
                        "total_tokens": len(json["texts"]) * 10,
                        "latency_ms": 50.0,
                    }
                else:
                    return {
                        "translation": f"translated_{json['text']}",
                        "tokens_used": 10,
                        "latency_ms": 50.0,
                    }

        return MockResponse()

    return mock_post


@pytest.fixture
async def service(mock_modal_response):
    """Create and start a batch translation service with mocked Modal."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = mock_modal_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        svc = BatchTranslationService(
            modal_endpoint="https://mock.modal.run",
            num_workers=2,
        )
        await svc.start()
        yield svc
        await svc.stop()


class TestFullTranslationFlow:
    """Test complete translation flow."""

    @pytest.mark.asyncio
    async def test_single_translation(self, service: BatchTranslationService) -> None:
        """Test single translation request."""
        result = await service.translate(
            text="Hello world",
            source_lang="en",
            target_lang="zh",
            user_id="user1",
            tier=UserTier.BASIC,
        )

        assert "translation" in result
        assert result["translation"] == "translated_Hello world"
        assert "latency_ms" in result
        assert "batch_size" in result

    @pytest.mark.asyncio
    async def test_batch_translation(self, service: BatchTranslationService) -> None:
        """Test batch translation request."""
        texts = ["Hello", "World", "Test"]
        results = await service.translate_batch(
            texts=texts,
            source_lang="en",
            target_lang="zh",
            user_id="user1",
            tier=UserTier.BASIC,
        )

        assert len(results) == 3
        assert results[0]["translation"] == "translated_Hello"
        assert results[1]["translation"] == "translated_World"
        assert results[2]["translation"] == "translated_Test"

    @pytest.mark.asyncio
    async def test_empty_batch(self, service: BatchTranslationService) -> None:
        """Test empty batch returns empty list."""
        results = await service.translate_batch(
            texts=[],
            source_lang="en",
            target_lang="zh",
            user_id="user1",
            tier=UserTier.BASIC,
        )

        assert results == []


class TestConcurrentUsers:
    """Test concurrent user handling."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, service: BatchTranslationService) -> None:
        """Test many concurrent translation requests."""
        num_users = 20
        requests_per_user = 5

        async def user_requests(user_id: int) -> list:
            results = []
            for i in range(requests_per_user):
                result = await service.translate(
                    text=f"text_{user_id}_{i}",
                    source_lang="en",
                    target_lang="zh",
                    user_id=f"user_{user_id}",
                    tier=UserTier.BASIC,
                )
                results.append(result)
            return results

        # Run all users concurrently
        tasks = [user_requests(i) for i in range(num_users)]
        all_results = await asyncio.gather(*tasks)

        # Verify all completed successfully
        total_results = sum(len(r) for r in all_results)
        assert total_results == num_users * requests_per_user


class TestTierDifferentiation:
    """Test tier-based prioritization."""

    @pytest.mark.asyncio
    async def test_tier_string_conversion(self, service: BatchTranslationService) -> None:
        """Test tier string is converted correctly."""
        result = await service.translate(
            text="test",
            source_lang="en",
            target_lang="zh",
            user_id="user1",
            tier="enterprise",  # String instead of enum
        )

        assert "translation" in result

    @pytest.mark.asyncio
    async def test_invalid_tier_defaults_to_free(self, service: BatchTranslationService) -> None:
        """Test invalid tier string defaults to FREE."""
        result = await service.translate(
            text="test",
            source_lang="en",
            target_lang="zh",
            user_id="user1",
            tier="invalid_tier",
        )

        # Should still work with FREE tier
        assert "translation" in result


class TestServiceLifecycle:
    """Test service start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_service_start_stop(self, mock_modal_response) -> None:
        """Test service can be started and stopped."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = mock_modal_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = BatchTranslationService()

            assert not service.is_running

            await service.start()
            assert service.is_running

            await service.stop()
            assert not service.is_running

    @pytest.mark.asyncio
    async def test_double_start_idempotent(self, service: BatchTranslationService) -> None:
        """Test starting twice is safe."""
        # Service already started in fixture
        await service.start()  # Should be idempotent
        assert service.is_running

    @pytest.mark.asyncio
    async def test_translate_without_start_raises(self) -> None:
        """Test translation without starting raises error."""
        service = BatchTranslationService()

        with pytest.raises(RuntimeError, match="not running"):
            await service.translate(
                text="test",
                source_lang="en",
                target_lang="zh",
                user_id="user1",
                tier=UserTier.BASIC,
            )


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_running(self, service: BatchTranslationService) -> None:
        """Test health check when service is running."""
        with patch.object(service.processor, "health_check", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = {"status": "healthy", "model_loaded": True}

            health = await service.health_check()

            assert health["running"] is True
            assert health["workers_active"] > 0


class TestMetrics:
    """Test metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_after_requests(self, service: BatchTranslationService) -> None:
        """Test metrics are tracked after requests."""
        # Make some requests
        for i in range(5):
            await service.translate(
                text=f"text_{i}",
                source_lang="en",
                target_lang="zh",
                user_id="user1",
                tier=UserTier.BASIC,
            )

        # Wait a bit for metrics to update
        await asyncio.sleep(0.1)

        metrics = service.get_metrics()

        assert metrics["service"]["running"] is True
        assert metrics["queue"]["total_enqueued"] >= 5

    @pytest.mark.asyncio
    async def test_metrics_reset(self, service: BatchTranslationService) -> None:
        """Test metrics can be reset."""
        await service.translate(
            text="test",
            source_lang="en",
            target_lang="zh",
            user_id="user1",
            tier=UserTier.BASIC,
        )

        await asyncio.sleep(0.1)
        service.reset_metrics()

        metrics = service.get_metrics()
        assert metrics["queue"]["total_enqueued"] == 0


class TestTimeout:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        """Test that timeout raises TimeoutError."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            async def slow_post(*args, **kwargs):
                await asyncio.sleep(10)  # Very slow

            mock_client.post = slow_post
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = BatchTranslationService()
            await service.start()

            try:
                with pytest.raises(asyncio.TimeoutError):
                    await service.translate(
                        text="test",
                        source_lang="en",
                        target_lang="zh",
                        user_id="user1",
                        tier=UserTier.BASIC,
                        timeout=0.1,  # Very short timeout
                    )
            finally:
                await service.stop()
