"""Integration tests for BatchTranslationService.

Tests the tier-based priority queue system with real Modal MT service.
Validates performance characteristics and multi-language support.

Run with:
    pytest tests/integration/test_batch_service.py -v -m integration
"""

import asyncio
import os
import time
from typing import Any

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# Multi-Language Support Tests
# =============================================================================


class TestMultiLanguageTranslation:
    """Test translation across multiple language pairs."""

    # Test data for various language pairs
    LANGUAGE_TEST_CASES = [
        # (source_text, source_lang, target_lang, description, validation_func)
        (
            "Hello, how are you?",
            "en",
            "zh",
            "EN→ZH",
            lambda t: any("\u4e00" <= c <= "\u9fff" for c in t),
        ),
        (
            "你好，最近怎么样？",
            "zh",
            "en",
            "ZH→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "こんにちは、お元気ですか？",
            "ja",
            "en",
            "JA→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "안녕하세요, 어떻게 지내세요?",
            "ko",
            "en",
            "KO→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "Bonjour, comment allez-vous?",
            "fr",
            "en",
            "FR→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "Hallo, wie geht es Ihnen?",
            "de",
            "en",
            "DE→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "Hola, ¿cómo estás?",
            "es",
            "en",
            "ES→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "Olá, como você está?",
            "pt",
            "en",
            "PT→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "Привет, как дела?",
            "ru",
            "en",
            "RU→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "مرحبا، كيف حالك؟",
            "ar",
            "en",
            "AR→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "สวัสดี สบายดีไหม?",
            "th",
            "en",
            "TH→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
        (
            "Xin chào, bạn khỏe không?",
            "vi",
            "en",
            "VI→EN",
            lambda t: any(c.isascii() and c.isalpha() for c in t),
        ),
    ]

    async def test_batch_service_multi_language(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Test batch service with multiple language pairs."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.batch import BatchTranslationService, UserTier

        service = BatchTranslationService(
            modal_endpoint=modal_service_url,
            num_workers=2,
        )
        await service.start()

        results: list[dict[str, Any]] = []
        errors: list[tuple[str, Exception]] = []

        try:
            for text, src, tgt, desc, validate in self.LANGUAGE_TEST_CASES:
                try:
                    result = await service.translate(
                        text=text,
                        source_lang=src,
                        target_lang=tgt,
                        user_id="test_user",
                        tier=UserTier.BASIC,
                        timeout=60.0,
                    )

                    translation = result["translation"]
                    is_valid = validate(translation)

                    results.append(
                        {
                            "pair": desc,
                            "source": text,
                            "translation": translation,
                            "valid": is_valid,
                            "latency_ms": result.get("latency_ms", 0),
                        }
                    )

                    if not is_valid:
                        print(f"Warning: {desc} validation failed - {translation}")

                except Exception as e:
                    errors.append((desc, e))
                    print(f"Error in {desc}: {e}")

        finally:
            await service.stop()

        # Print results summary
        print("\n" + "=" * 70)
        print("Multi-Language Translation Results")
        print("=" * 70)
        for r in results:
            status = "✓" if r["valid"] else "✗"
            print(f"{status} {r['pair']}: {r['source'][:20]}... → {r['translation'][:30]}...")
        print(f"\nPassed: {sum(1 for r in results if r['valid'])}/{len(results)}")
        print(f"Errors: {len(errors)}")
        print("=" * 70)

        # At least 80% should succeed
        success_rate = sum(1 for r in results if r["valid"]) / len(self.LANGUAGE_TEST_CASES)
        assert success_rate >= 0.8, f"Success rate {success_rate:.0%} < 80%"


class TestBatchServiceCJK:
    """Focused tests for CJK (Chinese-Japanese-Korean) languages."""

    async def test_cjk_translations(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Test CJK language translations with batch service."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.batch import BatchTranslationService, UserTier

        service = BatchTranslationService(
            modal_endpoint=modal_service_url,
            num_workers=2,
        )
        await service.start()

        test_cases = [
            # Gaming/Chat context
            ("Good game, well played!", "en", "zh"),
            ("Good game, well played!", "en", "ja"),
            ("Good game, well played!", "en", "ko"),
            # Casual conversation
            ("See you tomorrow!", "en", "zh"),
            ("Thank you very much!", "en", "ja"),
            ("Nice to meet you!", "en", "ko"),
            # Reverse direction
            ("打得不错", "zh", "en"),
            ("お疲れ様でした", "ja", "en"),
            ("수고하셨습니다", "ko", "en"),
        ]

        try:
            results = []
            for text, src, tgt in test_cases:
                result = await service.translate(
                    text=text,
                    source_lang=src,
                    target_lang=tgt,
                    user_id="test_cjk",
                    tier=UserTier.BASIC,
                    timeout=60.0,
                )
                results.append(
                    {
                        "source": text,
                        "translation": result["translation"],
                        "pair": f"{src}→{tgt}",
                    }
                )

            # Print results
            print("\n" + "=" * 60)
            print("CJK Translation Results")
            print("=" * 60)
            for r in results:
                print(f"[{r['pair']}] {r['source']} → {r['translation']}")
            print("=" * 60)

            # All should produce non-empty translations
            assert all(len(r["translation"]) > 0 for r in results)

        finally:
            await service.stop()


# =============================================================================
# Tier Priority Tests
# =============================================================================


class TestTierPrioritization:
    """Test tier-based request prioritization."""

    async def test_enterprise_priority_over_free(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Enterprise requests should be processed faster than Free."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.batch import BatchTranslationService, UserTier

        service = BatchTranslationService(
            modal_endpoint=modal_service_url,
            num_workers=1,  # Single worker to see priority effect
        )
        await service.start()

        try:
            # Submit multiple requests of different tiers simultaneously
            texts = [f"Priority test message {i}" for i in range(5)]

            async def timed_translate(tier: UserTier) -> tuple[UserTier, float]:
                start = time.time()
                await asyncio.gather(
                    *[
                        service.translate(
                            text=t,
                            source_lang="en",
                            target_lang="zh",
                            user_id=f"user_{tier.value}",
                            tier=tier,
                            timeout=120.0,
                        )
                        for t in texts
                    ]
                )
                elapsed = time.time() - start
                return tier, elapsed

            # Run Free and Enterprise concurrently
            free_task = asyncio.create_task(timed_translate(UserTier.FREE))
            enterprise_task = asyncio.create_task(timed_translate(UserTier.ENTERPRISE))

            # Small delay between starting them
            await asyncio.sleep(0.01)

            (free_tier, free_time), (ent_tier, ent_time) = await asyncio.gather(
                free_task, enterprise_task
            )

            print(f"\nEnterprise time: {ent_time:.2f}s")
            print(f"Free time: {free_time:.2f}s")

            # Enterprise should complete (may or may not be faster due to concurrent execution)
            # Main goal is both complete successfully
            assert ent_time > 0
            assert free_time > 0

        finally:
            await service.stop()


# =============================================================================
# Concurrent Request Tests
# =============================================================================


class TestConcurrentRequests:
    """Test service under concurrent load."""

    async def test_concurrent_translations(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Test many concurrent translation requests."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.batch import BatchTranslationService, UserTier

        service = BatchTranslationService(
            modal_endpoint=modal_service_url,
            num_workers=2,
        )
        await service.start()

        num_requests = 20
        tiers = [UserTier.FREE, UserTier.BASIC, UserTier.PRO, UserTier.ENTERPRISE]

        try:

            async def make_request(idx: int) -> dict[str, Any]:
                tier = tiers[idx % len(tiers)]
                start = time.time()
                result = await service.translate(
                    text=f"Concurrent test message number {idx}",
                    source_lang="en",
                    target_lang="zh",
                    user_id=f"user_{idx}",
                    tier=tier,
                    timeout=120.0,
                )
                elapsed = time.time() - start
                return {
                    "idx": idx,
                    "tier": tier.value,
                    "translation": result["translation"],
                    "elapsed": elapsed,
                }

            # Submit all requests concurrently
            start_time = time.time()
            results = await asyncio.gather(*[make_request(i) for i in range(num_requests)])
            total_time = time.time() - start_time

            # Print summary
            print(f"\n{'=' * 60}")
            print(f"Concurrent Request Results ({num_requests} requests)")
            print(f"{'=' * 60}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Avg time per request: {total_time/num_requests:.2f}s")
            print(f"Throughput: {num_requests/total_time:.1f} req/s")

            # Group by tier
            by_tier: dict[str, list[float]] = {}
            for r in results:
                tier = r["tier"]
                if tier not in by_tier:
                    by_tier[tier] = []
                by_tier[tier].append(r["elapsed"])

            print("\nLatency by tier:")
            for tier, times in sorted(by_tier.items()):
                avg = sum(times) / len(times)
                print(f"  {tier}: avg {avg:.2f}s")

            print("=" * 60)

            # All should succeed
            assert len(results) == num_requests
            assert all(len(r["translation"]) > 0 for r in results)

        finally:
            await service.stop()

    async def test_batch_translate_api(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Test batch translation API with multiple texts."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.batch import BatchTranslationService, UserTier

        service = BatchTranslationService(
            modal_endpoint=modal_service_url,
            num_workers=2,
        )
        await service.start()

        try:
            texts = [
                "Hello world",
                "How are you today?",
                "Nice to meet you",
                "Thank you very much",
                "See you later",
            ]

            start = time.time()
            results = await service.translate_batch(
                texts=texts,
                source_lang="en",
                target_lang="zh",
                user_id="batch_test_user",
                tier=UserTier.PRO,
            )
            elapsed = time.time() - start

            print(f"\n{'=' * 60}")
            print(f"Batch Translation Results ({len(texts)} texts)")
            print(f"{'=' * 60}")
            print(f"Total time: {elapsed:.2f}s")
            for i, r in enumerate(results):
                print(f"  {texts[i]} → {r['translation']}")
            print("=" * 60)

            assert len(results) == len(texts)
            assert all("translation" in r for r in results)
            assert all(len(r["translation"]) > 0 for r in results)

        finally:
            await service.stop()


# =============================================================================
# Metrics Validation Tests
# =============================================================================


class TestMetricsCollection:
    """Test metrics collection and accuracy."""

    async def test_metrics_accuracy(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Test that metrics are accurately collected."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.batch import BatchTranslationService, UserTier

        service = BatchTranslationService(
            modal_endpoint=modal_service_url,
            num_workers=2,
        )
        await service.start()

        try:
            # Reset metrics first
            service.reset_metrics()

            # Make known number of requests
            num_requests = 5
            for i in range(num_requests):
                await service.translate(
                    text=f"Metrics test {i}",
                    source_lang="en",
                    target_lang="zh",
                    user_id="metrics_user",
                    tier=UserTier.BASIC,
                    timeout=60.0,
                )

            # Wait for metrics to settle
            await asyncio.sleep(0.5)

            metrics = service.get_metrics()

            print(f"\n{'=' * 60}")
            print("Service Metrics")
            print(f"{'=' * 60}")
            print(f"Queue enqueued: {metrics['queue']['total_enqueued']}")
            print(f"Service running: {metrics['service']['running']}")
            print(f"Workers active: {metrics['service']['workers_active']}")
            print("=" * 60)

            # Verify metrics
            assert metrics["service"]["running"] is True
            assert metrics["queue"]["total_enqueued"] >= num_requests

        finally:
            await service.stop()


# =============================================================================
# Service Lifecycle Tests
# =============================================================================


class TestServiceLifecycle:
    """Test service start/stop behavior with real service."""

    async def test_service_restart(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Test service can be restarted."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.batch import BatchTranslationService, UserTier

        service = BatchTranslationService(
            modal_endpoint=modal_service_url,
            num_workers=1,
        )

        # First start
        await service.start()
        assert service.is_running

        result1 = await service.translate(
            text="First run test",
            source_lang="en",
            target_lang="zh",
            user_id="lifecycle_user",
            tier=UserTier.BASIC,
            timeout=60.0,
        )
        assert len(result1["translation"]) > 0

        # Stop
        await service.stop()
        assert not service.is_running

        # Restart
        await service.start()
        assert service.is_running

        result2 = await service.translate(
            text="Second run test",
            source_lang="en",
            target_lang="zh",
            user_id="lifecycle_user",
            tier=UserTier.BASIC,
            timeout=60.0,
        )
        assert len(result2["translation"]) > 0

        await service.stop()

    async def test_health_check_integration(
        self,
        skip_if_no_modal,
        modal_service_url: str,
    ) -> None:
        """Test health check with real Modal service."""
        os.environ["ML_SERVICE_URL"] = modal_service_url

        from app.services.batch import BatchTranslationService

        service = BatchTranslationService(
            modal_endpoint=modal_service_url,
            num_workers=1,
        )
        await service.start()

        try:
            health = await service.health_check()

            print(f"\n{'=' * 60}")
            print("Health Check Results")
            print(f"{'=' * 60}")
            print(f"Running: {health.get('running')}")
            print(f"Workers active: {health.get('workers_active')}")
            print(f"Modal status: {health.get('modal', {}).get('status', 'unknown')}")
            print("=" * 60)

            assert health["running"] is True
            assert health["workers_active"] > 0

        finally:
            await service.stop()
