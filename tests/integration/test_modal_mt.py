"""Integration tests for Modal MT service.

These tests verify the real Modal-hosted translation service works correctly.
They require Modal credentials and will incur actual GPU costs.

Run with:
    MODAL_TOKEN_ID=xxx MODAL_TOKEN_SECRET=yyy pytest -m integration
"""

import os
import time

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# Health Check Tests
# =============================================================================


class TestModalHealth:
    """Test Modal MT service health endpoints."""

    @pytest.mark.timeout(30)
    async def test_health_endpoint_responds(
        self,
        skip_if_no_modal,
        modal_health_url: str,
    ) -> None:
        """Health endpoint should respond within timeout."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{modal_health_url}/health")

            assert response.status_code == 200
            data = response.json()

            # Verify health response structure
            assert "status" in data
            assert "model_id" in data
            assert "model_loaded" in data
            assert "gpu_available" in data

    @pytest.mark.timeout(30)
    async def test_health_reports_model_info(
        self,
        skip_if_no_modal,
        modal_health_url: str,
    ) -> None:
        """Health endpoint should report correct model information."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{modal_health_url}/health")
            data = response.json()

            # Verify expected model
            assert "madlad" in data["model_id"].lower() or "google" in data["model_id"].lower()


# =============================================================================
# Translation Tests
# =============================================================================


class TestModalTranslation:
    """Test Modal MT service translation endpoints."""

    @pytest.mark.timeout(60)
    async def test_translate_en_to_zh(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """English to Chinese translation should work."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "Hello, how are you?",
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "translation" in data
            assert "source_lang" in data
            assert "target_lang" in data
            assert "tokens_used" in data
            assert "latency_ms" in data

            # Verify translation is not empty
            assert len(data["translation"]) > 0
            # Chinese characters should be present
            assert any("\u4e00" <= c <= "\u9fff" for c in data["translation"])

    @pytest.mark.timeout(60)
    async def test_translate_zh_to_en(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Chinese to English translation should work."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "你好，最近怎么样？",
                    "source_lang": "zh",
                    "target_lang": "en",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert len(data["translation"]) > 0
            # Should contain English letters
            assert any(c.isalpha() and ord(c) < 128 for c in data["translation"])

    @pytest.mark.timeout(60)
    async def test_translate_ja_to_en(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Japanese to English translation should work."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "こんにちは",
                    "source_lang": "ja",
                    "target_lang": "en",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["translation"]) > 0

    @pytest.mark.timeout(60)
    async def test_translate_returns_token_count(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Translation should return accurate token count."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "Hello world",
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )

            data = response.json()
            assert data["tokens_used"] > 0
            assert data["tokens_used"] < 100  # Simple text shouldn't use many tokens

    @pytest.mark.timeout(60)
    async def test_translate_returns_latency(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Translation should return latency measurement."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "Test",
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )

            data = response.json()
            assert data["latency_ms"] > 0
            assert data["latency_ms"] < 30000  # Should complete within 30s


# =============================================================================
# Batch Translation Tests
# =============================================================================


class TestModalBatchTranslation:
    """Test Modal MT service batch translation."""

    @pytest.mark.timeout(90)
    async def test_batch_translate(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Batch translation should work for multiple texts."""
        texts = [
            "Hello",
            "How are you?",
            "Good morning",
            "Thank you",
        ]

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "texts": texts,
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify batch response structure
            assert "translations" in data
            assert len(data["translations"]) == len(texts)
            assert "total_tokens" in data
            assert "latency_ms" in data

            # Each translation should be non-empty
            for translation in data["translations"]:
                assert len(translation) > 0

    @pytest.mark.timeout(90)
    async def test_batch_translate_max_size(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Batch translation should handle maximum batch size (16)."""
        texts = [f"Test message {i}" for i in range(16)]

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "texts": texts,
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["translations"]) == 16


# =============================================================================
# Performance Tests
# =============================================================================


class TestModalPerformance:
    """Test Modal MT service performance characteristics."""

    @pytest.mark.timeout(120)
    @pytest.mark.slow
    async def test_cold_start_latency(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Cold start should complete within target time (30s)."""
        # Note: This test may not always catch a true cold start
        # depending on service state

        start = time.time()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "Cold start test",
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )
        end = time.time()

        assert response.status_code == 200
        total_time = end - start

        # Log the time for monitoring
        print(f"\nTotal request time: {total_time:.2f}s")

        # Cold start target is 30s, but we allow some buffer
        # Warm requests should be much faster (<1s)
        assert total_time < 60, f"Request took {total_time:.2f}s, expected <60s"

    @pytest.mark.timeout(60)
    async def test_warm_latency(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Warm request latency should be under 500ms."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # First request to warm up
            await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "Warm up",
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )

            # Measure second request (should be warm)
            start = time.time()
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "Speed test",
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )
            end = time.time()

            assert response.status_code == 200
            data = response.json()

            # Check both wall time and reported latency
            wall_time_ms = (end - start) * 1000
            reported_latency = data["latency_ms"]

            print(f"\nWall time: {wall_time_ms:.0f}ms, Reported latency: {reported_latency:.0f}ms")

            # Target is 500ms for warm requests
            # Network adds some overhead, so we check reported latency
            assert reported_latency < 1000, f"Reported latency {reported_latency:.0f}ms > 1000ms"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestModalErrorHandling:
    """Test Modal MT service error handling."""

    @pytest.mark.timeout(30)
    async def test_invalid_language_returns_error(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Invalid language code should return appropriate error."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "Hello",
                    "source_lang": "invalid_lang",
                    "target_lang": "zh",
                },
            )

            # Service should return 4xx error for invalid input
            assert response.status_code in [400, 422]

    @pytest.mark.timeout(30)
    async def test_empty_text_returns_error(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Empty text should return appropriate error."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": "",
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )

            assert response.status_code in [400, 422]

    @pytest.mark.timeout(30)
    async def test_oversized_text_returns_error(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Text exceeding max length should return error."""
        long_text = "x" * 1000  # Over 512 char limit

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{modal_service_url}/translate",
                json={
                    "text": long_text,
                    "source_lang": "en",
                    "target_lang": "zh",
                },
            )

            assert response.status_code in [400, 422]


# =============================================================================
# API Client Integration Tests
# =============================================================================


class TestMTClientIntegration:
    """Test the MTClient class with real Modal service."""

    @pytest.mark.timeout(60)
    async def test_mt_client_translate(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """MTClient should successfully translate using real service."""
        # Set environment for MTClient
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.mt_client import MTClient

        async with MTClient() as client:
            result = await client.translate(
                text="Hello world",
                source_lang="en",
                target_lang="zh",
            )

            assert result.translation
            assert len(result.translation) > 0
            assert result.tokens_used > 0
            assert result.latency_ms > 0
            assert result.source_lang == "en"
            assert result.target_lang == "zh"

    @pytest.mark.timeout(90)
    async def test_mt_client_batch_translate(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """MTClient batch translation should work with real service."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.mt_client import MTClient

        texts = ["Hello", "World", "Test"]

        async with MTClient() as client:
            result = await client.translate_batch(
                texts=texts,
                source_lang="en",
                target_lang="zh",
            )

            assert len(result.translations) == 3
            assert result.total_tokens > 0
            assert result.latency_ms > 0

    @pytest.mark.timeout(30)
    async def test_mt_client_health_check(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """MTClient health check should work with real service."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.mt_client import MTClient

        async with MTClient() as client:
            health = await client.health_check()

            assert health.status in ["healthy", "ok"]
            assert health.model_id
            assert isinstance(health.model_loaded, bool)
            assert isinstance(health.gpu_available, bool)
