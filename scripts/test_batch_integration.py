#!/usr/bin/env python3
"""Integration test script for BatchTranslationService.

Tests the batch translation service with real Modal MT service.
Validates multi-language support and tier-based prioritization.

Usage:
    python scripts/test_batch_integration.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set Modal endpoint before importing app modules
MODAL_ENDPOINT = os.getenv("ML_SERVICE_URL", "https://nikmomo--unitra-mt-translate.modal.run")
os.environ["ML_SERVICE_URL"] = MODAL_ENDPOINT

from app.services.batch import BatchTranslationService, UserTier


# Test data for various language pairs
LANGUAGE_TEST_CASES = [
    # (source_text, source_lang, target_lang, description)
    ("Hello, how are you?", "en", "zh", "EN→ZH"),
    ("你好，最近怎么样？", "zh", "en", "ZH→EN"),
    ("こんにちは、お元気ですか？", "ja", "en", "JA→EN"),
    ("안녕하세요, 어떻게 지내세요?", "ko", "en", "KO→EN"),
    ("Bonjour, comment allez-vous?", "fr", "en", "FR→EN"),
    ("Hallo, wie geht es Ihnen?", "de", "en", "DE→EN"),
    ("Hola, ¿cómo estás?", "es", "en", "ES→EN"),
    ("Olá, como você está?", "pt", "en", "PT→EN"),
    ("Привет, как дела?", "ru", "en", "RU→EN"),
    ("สวัสดี สบายดีไหม?", "th", "en", "TH→EN"),
    ("Xin chào, bạn khỏe không?", "vi", "en", "VI→EN"),
]

# Gaming context tests (CJK focus)
GAMING_TEST_CASES = [
    ("Good game, well played!", "en", "zh"),
    ("Good game, well played!", "en", "ja"),
    ("Good game, well played!", "en", "ko"),
    ("打得不错，下次再来！", "zh", "en"),
    ("お疲れ様でした", "ja", "en"),
    ("수고하셨습니다", "ko", "en"),
]


async def test_multi_language():
    """Test translation across multiple languages."""
    print("\n" + "=" * 70)
    print("TEST: Multi-Language Translation")
    print("=" * 70)

    service = BatchTranslationService(modal_endpoint=MODAL_ENDPOINT, num_workers=2)
    await service.start()

    results = []
    errors = []

    try:
        for text, src, tgt, desc in LANGUAGE_TEST_CASES:
            try:
                start = time.time()
                result = await service.translate(
                    text=text,
                    source_lang=src,
                    target_lang=tgt,
                    user_id="test_user",
                    tier=UserTier.BASIC,
                    timeout=90.0,
                )
                elapsed = (time.time() - start) * 1000

                results.append(
                    {
                        "pair": desc,
                        "source": text,
                        "translation": result["translation"],
                        "latency_ms": elapsed,
                    }
                )
                print(
                    f"✓ {desc}: {text[:25]}... → {result['translation'][:30]}... ({elapsed:.0f}ms)"
                )

            except Exception as e:
                errors.append((desc, str(e)))
                print(f"✗ {desc}: ERROR - {e}")

    finally:
        await service.stop()

    print("\n" + "-" * 70)
    print(f"Results: {len(results)}/{len(LANGUAGE_TEST_CASES)} passed, {len(errors)} errors")

    if results:
        avg_latency = sum(r["latency_ms"] for r in results) / len(results)
        print(f"Avg latency: {avg_latency:.0f}ms")

    return len(errors) == 0


async def test_gaming_context():
    """Test gaming-context translations (CJK focus)."""
    print("\n" + "=" * 70)
    print("TEST: Gaming Context Translations (CJK)")
    print("=" * 70)

    service = BatchTranslationService(modal_endpoint=MODAL_ENDPOINT, num_workers=2)
    await service.start()

    results = []

    try:
        for text, src, tgt in GAMING_TEST_CASES:
            result = await service.translate(
                text=text,
                source_lang=src,
                target_lang=tgt,
                user_id="gamer",
                tier=UserTier.PRO,
                timeout=90.0,
            )
            results.append(
                {
                    "source": text,
                    "translation": result["translation"],
                    "pair": f"{src}→{tgt}",
                }
            )
            print(f"✓ [{src}→{tgt}] {text} → {result['translation']}")

    finally:
        await service.stop()

    print(f"\nCompleted: {len(results)}/{len(GAMING_TEST_CASES)}")
    return len(results) == len(GAMING_TEST_CASES)


async def test_batch_translation():
    """Test batch translation API."""
    print("\n" + "=" * 70)
    print("TEST: Batch Translation")
    print("=" * 70)

    service = BatchTranslationService(modal_endpoint=MODAL_ENDPOINT, num_workers=2)
    await service.start()

    texts = [
        "Hello world",
        "How are you today?",
        "Nice to meet you",
        "Thank you very much",
        "See you later",
        "Good morning",
        "Good night",
        "Have a nice day",
    ]

    try:
        start = time.time()
        results = await service.translate_batch(
            texts=texts,
            source_lang="en",
            target_lang="zh",
            user_id="batch_user",
            tier=UserTier.BASIC,
        )
        elapsed = time.time() - start

        print(f"Batch of {len(texts)} texts completed in {elapsed:.2f}s")
        print(f"Throughput: {len(texts)/elapsed:.1f} texts/s")
        print("\nTranslations:")
        for i, r in enumerate(results):
            print(f"  {i+1}. {texts[i]} → {r['translation']}")

    finally:
        await service.stop()

    return len(results) == len(texts)


async def test_tier_comparison():
    """Test tier-based processing comparison."""
    print("\n" + "=" * 70)
    print("TEST: Tier Comparison")
    print("=" * 70)

    service = BatchTranslationService(modal_endpoint=MODAL_ENDPOINT, num_workers=2)
    await service.start()

    tiers = [UserTier.FREE, UserTier.BASIC, UserTier.PRO, UserTier.ENTERPRISE]
    tier_times = {}

    try:
        for tier in tiers:
            texts = [f"Tier {tier.value} test message {i}" for i in range(3)]

            start = time.time()
            for text in texts:
                await service.translate(
                    text=text,
                    source_lang="en",
                    target_lang="zh",
                    user_id=f"user_{tier.value}",
                    tier=tier,
                    timeout=90.0,
                )
            elapsed = time.time() - start

            tier_times[tier.value] = elapsed
            print(
                f"{tier.value.upper():12} - {len(texts)} requests in {elapsed:.2f}s ({elapsed/len(texts):.2f}s/req)"
            )

    finally:
        await service.stop()

    return True


async def test_concurrent_requests():
    """Test concurrent request handling."""
    print("\n" + "=" * 70)
    print("TEST: Concurrent Requests")
    print("=" * 70)

    service = BatchTranslationService(modal_endpoint=MODAL_ENDPOINT, num_workers=2)
    await service.start()

    num_requests = 10

    try:

        async def make_request(idx: int) -> dict:
            tier = [UserTier.FREE, UserTier.BASIC, UserTier.PRO, UserTier.ENTERPRISE][idx % 4]
            result = await service.translate(
                text=f"Concurrent test {idx}",
                source_lang="en",
                target_lang="zh",
                user_id=f"user_{idx}",
                tier=tier,
                timeout=120.0,
            )
            return {"idx": idx, "tier": tier.value, "translation": result["translation"]}

        start = time.time()
        results = await asyncio.gather(*[make_request(i) for i in range(num_requests)])
        elapsed = time.time() - start

        print(f"Completed {num_requests} concurrent requests in {elapsed:.2f}s")
        print(f"Throughput: {num_requests/elapsed:.1f} req/s")

    finally:
        await service.stop()

    return len(results) == num_requests


async def test_metrics():
    """Test metrics collection."""
    print("\n" + "=" * 70)
    print("TEST: Metrics Collection")
    print("=" * 70)

    service = BatchTranslationService(modal_endpoint=MODAL_ENDPOINT, num_workers=2)
    await service.start()

    try:
        service.reset_metrics()

        # Make some requests
        for i in range(5):
            await service.translate(
                text=f"Metrics test {i}",
                source_lang="en",
                target_lang="zh",
                user_id="metrics_user",
                tier=UserTier.BASIC,
                timeout=60.0,
            )

        await asyncio.sleep(0.5)
        metrics = service.get_metrics()

        print("Service Metrics:")
        print(f"  Running: {metrics['service']['running']}")
        print(f"  Workers: {metrics['service']['workers_active']}")
        print(f"  Queue enqueued: {metrics['queue']['total_enqueued']}")
        print(f"  Queue size: {metrics['queue']['size']}")

    finally:
        await service.stop()

    return metrics["queue"]["total_enqueued"] >= 5  # Should have processed 5 requests


async def main():
    """Run all integration tests."""
    print("=" * 70)
    print("BATCH TRANSLATION SERVICE - INTEGRATION TESTS")
    print("=" * 70)
    print(f"Modal endpoint: https://nikmomo--unitra-mt-translate.modal.run")
    print(f"Starting tests...")

    tests = [
        ("Multi-Language", test_multi_language),
        ("Gaming Context", test_gaming_context),
        ("Batch Translation", test_batch_translation),
        ("Tier Comparison", test_tier_comparison),
        ("Concurrent Requests", test_concurrent_requests),
        ("Metrics", test_metrics),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            passed = await test_fn()
            results[name] = "PASS" if passed else "FAIL"
        except Exception as e:
            print(f"\nERROR in {name}: {e}")
            results[name] = f"ERROR: {e}"

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, status in results.items():
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon} {name}: {status}")

    passed = sum(1 for s in results.values() if s == "PASS")
    print(f"\nTotal: {passed}/{len(tests)} tests passed")
    print("=" * 70)

    return all(s == "PASS" for s in results.values())


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
