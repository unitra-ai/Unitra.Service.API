"""Test priority queue behavior.

Test cases:
1. Priority ordering by tier
2. Starvation prevention via time boost
3. Dynamic priority calculation
4. Concurrent access safety
5. Queue metrics accuracy
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from app.services.batch.config import UserTier
from app.services.batch.queue import TranslationQueue, TranslationRequest


class TestPriorityOrdering:
    """Test that requests are dequeued in priority order."""

    @pytest.mark.asyncio
    async def test_priority_ordering_by_tier(self) -> None:
        """Submit different tier requests, verify dequeue order."""
        queue = TranslationQueue()

        # Submit in random order
        requests = [
            TranslationRequest(
                text="free", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.FREE
            ),
            TranslationRequest(
                text="enterprise", source_lang="en", target_lang="zh",
                user_id="u2", tier=UserTier.ENTERPRISE
            ),
            TranslationRequest(
                text="basic", source_lang="en", target_lang="zh",
                user_id="u3", tier=UserTier.BASIC
            ),
            TranslationRequest(
                text="pro", source_lang="en", target_lang="zh",
                user_id="u4", tier=UserTier.PRO
            ),
        ]

        for req in requests:
            await queue.put(req)

        # Dequeue should be: Enterprise, Pro, Basic, Free
        result1 = await queue.get(timeout=0.1)
        assert result1 is not None
        assert result1.tier == UserTier.ENTERPRISE

        result2 = await queue.get(timeout=0.1)
        assert result2 is not None
        assert result2.tier == UserTier.PRO

        result3 = await queue.get(timeout=0.1)
        assert result3 is not None
        assert result3.tier == UserTier.BASIC

        result4 = await queue.get(timeout=0.1)
        assert result4 is not None
        assert result4.tier == UserTier.FREE

    @pytest.mark.asyncio
    async def test_same_tier_fifo(self) -> None:
        """Requests of same tier should be FIFO."""
        queue = TranslationQueue()

        for i in range(5):
            req = TranslationRequest(
                text=f"text_{i}", source_lang="en", target_lang="zh",
                user_id=f"u{i}", tier=UserTier.BASIC
            )
            await queue.put(req)
            await asyncio.sleep(0.01)  # Small delay to ensure order

        # Should come out in order
        for i in range(5):
            result = await queue.get(timeout=0.1)
            assert result is not None
            assert result.text == f"text_{i}"


class TestStarvationPrevention:
    """Test that time boost prevents starvation."""

    @pytest.mark.asyncio
    async def test_starvation_prevention(self) -> None:
        """Free request waiting long enough should beat new Enterprise."""
        queue = TranslationQueue(starvation_boost_per_sec=0.5)

        # Submit Free request with old timestamp (8 seconds ago)
        old_time = time.time() - 8
        free_req = TranslationRequest(
            text="free_old", source_lang="en", target_lang="zh",
            user_id="u1", tier=UserTier.FREE
        )
        free_req.timestamp = old_time
        await queue.put(free_req)

        # Submit new Enterprise request
        enterprise_req = TranslationRequest(
            text="enterprise_new", source_lang="en", target_lang="zh",
            user_id="u2", tier=UserTier.ENTERPRISE
        )
        await queue.put(enterprise_req)

        # Free should be processed first due to time boost
        # Free priority: -(1 + 8*0.5) = -5
        # Enterprise priority: -(4 + 0) = -4
        result = await queue.get(timeout=0.1)
        assert result is not None
        assert result.text == "free_old"

    @pytest.mark.asyncio
    async def test_priority_calculation(self) -> None:
        """Test dynamic priority calculation."""
        req = TranslationRequest(
            text="test", source_lang="en", target_lang="zh",
            user_id="u1", tier=UserTier.BASIC
        )

        # Initial priority
        initial_priority = req.get_priority(starvation_boost_per_sec=0.5)

        # Simulate time passing
        req.timestamp = time.time() - 2  # 2 seconds ago
        later_priority = req.get_priority(starvation_boost_per_sec=0.5)

        # Priority should have increased (more negative)
        assert later_priority < initial_priority


class TestConcurrentAccess:
    """Test thread safety under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_put_get(self) -> None:
        """Test concurrent enqueue and dequeue operations."""
        queue = TranslationQueue()
        num_requests = 100
        results: list[TranslationRequest] = []

        async def producer() -> None:
            for i in range(num_requests):
                req = TranslationRequest(
                    text=f"text_{i}", source_lang="en", target_lang="zh",
                    user_id=f"u{i}", tier=UserTier.BASIC
                )
                await queue.put(req)
                await asyncio.sleep(0.001)

        async def consumer() -> None:
            while len(results) < num_requests:
                result = await queue.get(timeout=0.5)
                if result:
                    results.append(result)

        # Run producer and consumer concurrently
        await asyncio.gather(producer(), consumer())

        # Verify all requests were processed
        assert len(results) == num_requests

    @pytest.mark.asyncio
    async def test_multiple_consumers(self) -> None:
        """Test multiple concurrent consumers."""
        queue = TranslationQueue()
        num_requests = 50
        results: list[TranslationRequest] = []
        lock = asyncio.Lock()

        # Pre-fill queue
        for i in range(num_requests):
            req = TranslationRequest(
                text=f"text_{i}", source_lang="en", target_lang="zh",
                user_id=f"u{i}", tier=UserTier.BASIC
            )
            await queue.put(req)

        async def consumer(consumer_id: int) -> None:
            while True:
                result = await queue.get(timeout=0.1)
                if result is None:
                    break
                async with lock:
                    results.append(result)

        # Run multiple consumers
        consumers = [consumer(i) for i in range(5)]
        await asyncio.gather(*consumers)

        # Verify all requests were processed exactly once
        assert len(results) == num_requests
        texts = {r.text for r in results}
        assert len(texts) == num_requests  # No duplicates


class TestQueueMetrics:
    """Test queue metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(self) -> None:
        """Test that metrics are correctly tracked."""
        queue = TranslationQueue()

        # Submit requests of different tiers
        for tier in [UserTier.FREE, UserTier.BASIC, UserTier.PRO, UserTier.ENTERPRISE]:
            req = TranslationRequest(
                text="test", source_lang="en", target_lang="zh",
                user_id="u1", tier=tier
            )
            await queue.put(req)

        metrics = queue.get_metrics()
        assert metrics["size"] == 4
        assert metrics["total_enqueued"] == 4
        assert metrics["tier_distribution"]["free"] == 1
        assert metrics["tier_distribution"]["enterprise"] == 1

        # Dequeue some
        await queue.get(timeout=0.1)
        await queue.get(timeout=0.1)

        metrics = queue.get_metrics()
        assert metrics["size"] == 2
        assert metrics["total_dequeued"] == 2

    @pytest.mark.asyncio
    async def test_metrics_reset(self) -> None:
        """Test metrics reset functionality."""
        queue = TranslationQueue()

        for _ in range(5):
            req = TranslationRequest(
                text="test", source_lang="en", target_lang="zh",
                user_id="u1", tier=UserTier.BASIC
            )
            await queue.put(req)
            await queue.get(timeout=0.1)

        queue.reset_metrics()
        metrics = queue.get_metrics()

        assert metrics["total_enqueued"] == 0
        assert metrics["total_dequeued"] == 0


class TestQueueOperations:
    """Test basic queue operations."""

    @pytest.mark.asyncio
    async def test_empty_queue_timeout(self) -> None:
        """Test that get() times out on empty queue."""
        queue = TranslationQueue()

        result = await queue.get(timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_peek_operations(self) -> None:
        """Test peek operations without removing items."""
        queue = TranslationQueue()

        req = TranslationRequest(
            text="test", source_lang="en", target_lang="zh",
            user_id="u1", tier=UserTier.PRO
        )
        await queue.put(req)

        # Peek should return priority without removing
        priority = await queue.peek_priority()
        assert priority is not None
        assert queue.qsize() == 1

        tier = await queue.peek_tier()
        assert tier == UserTier.PRO
        assert queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_qsize_and_empty(self) -> None:
        """Test size tracking."""
        queue = TranslationQueue()

        assert queue.empty()
        assert queue.qsize() == 0

        req = TranslationRequest(
            text="test", source_lang="en", target_lang="zh",
            user_id="u1", tier=UserTier.BASIC
        )
        await queue.put(req)

        assert not queue.empty()
        assert queue.qsize() == 1
