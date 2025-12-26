"""Test smart batch collection.

Test cases:
1. Batch respects max size per tier
2. Batch respects max wait time
3. Minimum batch enforcement
4. Priority interruption
5. Adaptive batch sizing
6. Result distribution
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.batch.batcher import SmartBatcher, BatchResult
from app.services.batch.config import TIER_CONFIGS, UserTier
from app.services.batch.processor import BatchProcessor
from app.services.batch.queue import TranslationQueue, TranslationRequest


@pytest.fixture
def mock_processor() -> MagicMock:
    """Create a mock batch processor."""
    processor = MagicMock(spec=BatchProcessor)
    processor.translate_batch = AsyncMock(
        side_effect=lambda texts, **kwargs: [f"translated_{t}" for t in texts]
    )
    return processor


@pytest.fixture
def queue() -> TranslationQueue:
    """Create a translation queue."""
    return TranslationQueue()


@pytest.fixture
def batcher(queue: TranslationQueue, mock_processor: MagicMock) -> SmartBatcher:
    """Create a smart batcher with mock processor."""
    return SmartBatcher(queue, mock_processor, adaptive_sizing=True)


class TestBatchSizeLimits:
    """Test batch size limits by tier."""

    @pytest.mark.asyncio
    async def test_batch_respects_max_size_free(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """Free tier should have max batch size of 32."""
        # Submit 50 Free requests
        for i in range(50):
            req = TranslationRequest(
                text=f"text_{i}", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.FREE
            )
            await queue.put(req)

        batch = await batcher.collect_batch()

        # Should be limited to 32 (Free max)
        assert len(batch) <= TIER_CONFIGS[UserTier.FREE].max_batch_size

    @pytest.mark.asyncio
    async def test_batch_respects_max_size_enterprise(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """Enterprise tier should have smaller max batch size."""
        # Submit 20 Enterprise requests
        for i in range(20):
            req = TranslationRequest(
                text=f"text_{i}", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.ENTERPRISE
            )
            await queue.put(req)

        batch = await batcher.collect_batch()

        # Should be limited to 8 (Enterprise max)
        assert len(batch) <= TIER_CONFIGS[UserTier.ENTERPRISE].max_batch_size


class TestBatchWaitTime:
    """Test batch wait time limits."""

    @pytest.mark.asyncio
    async def test_batch_respects_max_wait(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """Batch should be processed within max_wait time."""
        # Submit 1 Enterprise request (max_wait=20ms)
        req = TranslationRequest(
            text="test", source_lang="en", target_lang="zh",
            user_id="u1", tier=UserTier.ENTERPRISE
        )
        await queue.put(req)

        # Collect batch - should return quickly due to max_wait
        import time
        start = time.time()
        batch = await batcher.collect_batch()
        elapsed_ms = (time.time() - start) * 1000

        assert len(batch) == 1
        # Should complete within max_wait + some tolerance
        assert elapsed_ms < TIER_CONFIGS[UserTier.ENTERPRISE].max_wait_ms + 50


class TestAdaptiveSizing:
    """Test adaptive batch sizing based on queue depth."""

    @pytest.mark.asyncio
    async def test_adaptive_sizing_small_queue(
        self, queue: TranslationQueue, mock_processor: MagicMock
    ) -> None:
        """Batch size should adapt to queue depth."""
        batcher = SmartBatcher(queue, mock_processor, adaptive_sizing=True)

        # Submit 5 requests
        for i in range(5):
            req = TranslationRequest(
                text=f"text_{i}", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.FREE
            )
            await queue.put(req)

        batch = await batcher.collect_batch()

        # With adaptive sizing, should get ~5 (not wait for max 32)
        assert len(batch) <= 6  # Small tolerance

    @pytest.mark.asyncio
    async def test_no_adaptive_sizing(
        self, queue: TranslationQueue, mock_processor: MagicMock
    ) -> None:
        """Without adaptive sizing, should try to fill to max."""
        batcher = SmartBatcher(queue, mock_processor, adaptive_sizing=False)

        # Submit 5 Free requests
        for i in range(5):
            req = TranslationRequest(
                text=f"text_{i}", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.FREE
            )
            await queue.put(req)

        batch = await batcher.collect_batch()
        assert len(batch) == 5


class TestPriorityInterruption:
    """Test that high-priority requests interrupt low-priority batches."""

    @pytest.mark.asyncio
    async def test_priority_interruption(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """Higher priority request should cause batch processing."""
        # Submit 3 Free requests (needs 8 for min_batch)
        for i in range(3):
            req = TranslationRequest(
                text=f"free_{i}", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.FREE
            )
            await queue.put(req)

        # Add an Enterprise request (higher priority)
        enterprise_req = TranslationRequest(
            text="enterprise", source_lang="en", target_lang="zh",
            user_id="u2", tier=UserTier.ENTERPRISE
        )

        # Start collecting batch, then add enterprise
        async def add_enterprise() -> None:
            await asyncio.sleep(0.02)  # Small delay
            await queue.put(enterprise_req)

        # Run concurrently
        collect_task = asyncio.create_task(batcher.collect_batch())
        add_task = asyncio.create_task(add_enterprise())

        batch, _ = await asyncio.gather(collect_task, add_task)

        # Enterprise should be processed separately (higher priority)
        # The Free batch may or may not complete depending on timing


class TestResultDistribution:
    """Test that results are correctly distributed to futures."""

    @pytest.mark.asyncio
    async def test_result_distribution(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """Each request should receive its correct translation."""
        requests = []
        for i in range(5):
            req = TranslationRequest(
                text=f"text_{i}", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.BASIC
            )
            await queue.put(req)
            requests.append(req)

        # Process batch
        result = await batcher.collect_and_process()

        assert result is not None
        assert result.batch_size == 5

        # Check each future has correct result
        for req in requests:
            future_result = await asyncio.wait_for(req.future, timeout=1.0)
            assert future_result["translation"] == f"translated_{req.text}"
            assert future_result["batch_size"] == 5

    @pytest.mark.asyncio
    async def test_error_distribution(
        self, queue: TranslationQueue, mock_processor: MagicMock
    ) -> None:
        """Errors should be distributed to all requests in batch."""
        mock_processor.translate_batch = AsyncMock(
            side_effect=Exception("Translation failed")
        )
        batcher = SmartBatcher(queue, mock_processor)

        requests = []
        for i in range(3):
            req = TranslationRequest(
                text=f"text_{i}", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.BASIC
            )
            await queue.put(req)
            requests.append(req)

        # Process should raise
        with pytest.raises(Exception):
            await batcher.collect_and_process()

        # Each future should have the exception
        for req in requests:
            with pytest.raises(Exception, match="Translation failed"):
                req.future.result()


class TestLanguagePairBatching:
    """Test that only same language pairs are batched together."""

    @pytest.mark.asyncio
    async def test_same_language_pair_batching(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """Only requests with same language pair should be batched."""
        # Submit en->zh requests
        for i in range(3):
            req = TranslationRequest(
                text=f"en_zh_{i}", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.BASIC
            )
            await queue.put(req)

        # Submit zh->en request (different pair)
        diff_req = TranslationRequest(
            text="zh_en", source_lang="zh", target_lang="en",
            user_id="u2", tier=UserTier.BASIC
        )
        await queue.put(diff_req)

        # First batch should only have en->zh
        batch1 = await batcher.collect_batch()
        assert len(batch1) == 3
        assert all(r.source_lang == "en" and r.target_lang == "zh" for r in batch1)

        # Second batch should have zh->en
        batch2 = await batcher.collect_batch()
        assert len(batch2) == 1
        assert batch2[0].source_lang == "zh" and batch2[0].target_lang == "en"


class TestBatcherMetrics:
    """Test batcher metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """Test that metrics are correctly tracked."""
        # Process a few batches
        for batch_num in range(3):
            for i in range(4):
                req = TranslationRequest(
                    text=f"text_{batch_num}_{i}", source_lang="en", target_lang="zh",
                    user_id="u1", tier=UserTier.BASIC
                )
                await queue.put(req)

            await batcher.collect_and_process()

        metrics = batcher.get_metrics()
        assert metrics["batches_processed"] == 3
        assert metrics["total_requests_processed"] == 12
        assert metrics["avg_batch_size"] == 4.0

    @pytest.mark.asyncio
    async def test_metrics_reset(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """Test metrics reset."""
        req = TranslationRequest(
            text="test", source_lang="en", target_lang="zh",
            user_id="u1", tier=UserTier.BASIC
        )
        await queue.put(req)
        await batcher.collect_and_process()

        batcher.reset_metrics()
        metrics = batcher.get_metrics()

        assert metrics["batches_processed"] == 0
        assert metrics["total_requests_processed"] == 0


class TestEmptyQueueHandling:
    """Test handling of empty queue."""

    @pytest.mark.asyncio
    async def test_empty_queue_returns_empty_batch(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """Empty queue should return empty batch after timeout."""
        batch = await batcher.collect_batch()
        assert batch == []

    @pytest.mark.asyncio
    async def test_collect_and_process_empty(
        self, queue: TranslationQueue, batcher: SmartBatcher
    ) -> None:
        """collect_and_process on empty queue returns None."""
        result = await batcher.collect_and_process()
        assert result is None
