"""Priority queue for translation requests.

Priority calculation:
- Base priority from tier (Enterprise=4, Pro=3, Basic=2, Free=1)
- Time boost: +0.5 priority per second waiting (prevents starvation)
- Final priority = -(base + time_boost) for min-heap

Example:
- Enterprise request arrives: priority = -4
- Free request waiting 8 seconds: priority = -(1 + 4) = -5 (higher priority!)

This ensures:
1. Higher tiers are processed first
2. No request waits forever (starvation prevention)
3. Fair degradation under load
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import TYPE_CHECKING, Any

from app.services.batch.config import TIER_CONFIGS, UserTier

if TYPE_CHECKING:
    from asyncio import Future


@dataclass
class TranslationRequest:
    """A single translation request in the queue."""

    text: str
    source_lang: str
    target_lang: str
    user_id: str
    tier: UserTier
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    future: Future[dict[str, Any]] = field(
        default_factory=lambda: asyncio.get_event_loop().create_future()
    )

    def get_priority(self, starvation_boost_per_sec: float = 0.5) -> float:
        """Calculate dynamic priority.

        Returns negative value for min-heap (more negative = higher priority).

        Args:
            starvation_boost_per_sec: Priority boost per second waiting

        Returns:
            Negative priority value for heap ordering
        """
        base_priority = TIER_CONFIGS[self.tier].priority
        wait_time_sec = time.time() - self.timestamp
        time_boost = wait_time_sec * starvation_boost_per_sec

        return -(base_priority + time_boost)

    def get_wait_time_ms(self) -> float:
        """Get how long this request has been waiting in milliseconds."""
        return (time.time() - self.timestamp) * 1000


@dataclass(order=True)
class PrioritizedRequest:
    """Wrapper for heap operations with priority comparison."""

    priority: float
    request: TranslationRequest = field(compare=False)


class TranslationQueue:
    """Thread-safe async priority queue for translation requests.

    Features:
    - Dynamic priority calculation
    - Starvation prevention via time boost
    - Tier-aware batching support
    - Metrics tracking
    """

    def __init__(self, starvation_boost_per_sec: float = 0.5):
        """Initialize the queue.

        Args:
            starvation_boost_per_sec: Priority boost per second waiting
        """
        self._heap: list[PrioritizedRequest] = []
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()
        self._size = 0
        self._starvation_boost = starvation_boost_per_sec

        # Metrics
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._tier_counts: dict[UserTier, int] = {t: 0 for t in UserTier}

    async def put(self, request: TranslationRequest) -> None:
        """Add a request to the queue.

        Args:
            request: Translation request to enqueue
        """
        async with self._lock:
            priority = request.get_priority(self._starvation_boost)
            heappush(self._heap, PrioritizedRequest(priority, request))
            self._size += 1
            self._total_enqueued += 1
            self._tier_counts[request.tier] += 1
            self._not_empty.set()

    async def get(self, timeout: float | None = None) -> TranslationRequest | None:
        """Get highest priority request.

        Args:
            timeout: Max seconds to wait (None = wait forever)

        Returns:
            TranslationRequest or None if timeout
        """
        # Wait for item if empty
        while self._size == 0:
            if timeout is not None:
                try:
                    await asyncio.wait_for(self._not_empty.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    return None
            else:
                await self._not_empty.wait()

        async with self._lock:
            if self._heap:
                # Re-sort by updated priorities before popping
                self._reheapify()
                item = heappop(self._heap)
                self._size -= 1
                self._total_dequeued += 1

                if self._size == 0:
                    self._not_empty.clear()

                return item.request
            return None

    async def get_batch(
        self,
        max_size: int,
        max_wait_ms: float,
        min_size: int = 1,
    ) -> list[TranslationRequest]:
        """Get a batch of requests for processing.

        Args:
            max_size: Maximum batch size
            max_wait_ms: Maximum time to wait for batch
            min_size: Minimum batch size before processing

        Returns:
            List of requests (may be smaller than min_size on timeout)
        """
        batch: list[TranslationRequest] = []
        start_time = time.time()
        max_wait_sec = max_wait_ms / 1000.0

        while len(batch) < max_size:
            elapsed = time.time() - start_time
            remaining = max_wait_sec - elapsed

            if remaining <= 0:
                break

            # Try to get a request
            request = await self.get(timeout=remaining)
            if request is None:
                break

            batch.append(request)

            # If we have min batch and more waiting, check if we should stop
            if len(batch) >= min_size and self._size > 0:
                # Continue collecting for efficiency
                pass

        return batch

    def _reheapify(self) -> None:
        """Recalculate priorities and rebuild heap.

        Called before dequeue to ensure time-boosted priorities are current.
        """
        # Update priorities for all items
        updated = [
            PrioritizedRequest(
                req.request.get_priority(self._starvation_boost),
                req.request,
            )
            for req in self._heap
        ]
        self._heap = []
        for item in updated:
            heappush(self._heap, item)

    async def peek_priority(self) -> float | None:
        """Check priority of next request without removing it.

        Returns:
            Priority of next request or None if empty
        """
        async with self._lock:
            if self._heap:
                # Return recalculated priority
                return self._heap[0].request.get_priority(self._starvation_boost)
            return None

    async def peek_tier(self) -> UserTier | None:
        """Check tier of next request without removing it.

        Returns:
            Tier of next request or None if empty
        """
        async with self._lock:
            if self._heap:
                return self._heap[0].request.tier
            return None

    def qsize(self) -> int:
        """Current queue size."""
        return self._size

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._size == 0

    def get_metrics(self) -> dict[str, Any]:
        """Get queue metrics.

        Returns:
            Dictionary with queue statistics
        """
        return {
            "size": self._size,
            "total_enqueued": self._total_enqueued,
            "total_dequeued": self._total_dequeued,
            "tier_distribution": {t.value: c for t, c in self._tier_counts.items()},
        }

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._tier_counts = {t: 0 for t in UserTier}
