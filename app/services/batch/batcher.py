"""Smart batch collector with tier-aware logic.

Batch collection strategy:
1. Pop first request to determine batch configuration
2. Collect more requests until:
   a) max_batch_size reached
   b) max_wait_ms exceeded
   c) min_batch_size reached AND higher-priority request waiting
3. Process batch and distribute results

Key optimizations:
- Dynamic batch sizing based on load
- Priority-aware collection (don't make Enterprise wait for Free batch)
- Minimum batch enforcement for cost efficiency
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from app.services.batch.config import TIER_CONFIGS
from app.services.batch.queue import TranslationQueue, TranslationRequest

if TYPE_CHECKING:
    from app.services.batch.processor import BatchProcessor

logger = structlog.get_logger(__name__)


@dataclass
class BatchResult:
    """Result of batch processing."""

    requests: list[TranslationRequest]
    translations: list[str]
    batch_size: int
    collect_time_ms: float
    process_time_ms: float
    total_time_ms: float
    tier_breakdown: dict[str, int]


class SmartBatcher:
    """Collects requests into efficient batches.

    Design goals:
    - Maximize GPU utilization (prefer larger batches)
    - Respect tier SLAs (don't exceed max_wait)
    - Prevent priority inversion (high-tier shouldn't wait for low-tier batch)
    """

    def __init__(
        self,
        queue: TranslationQueue,
        processor: BatchProcessor,
        adaptive_sizing: bool = True,
    ):
        """Initialize the batcher.

        Args:
            queue: Translation queue to pull from
            processor: Batch processor for GPU inference
            adaptive_sizing: Whether to adapt batch size to queue depth
        """
        self.queue = queue
        self.processor = processor
        self.adaptive_sizing = adaptive_sizing

        # Metrics
        self._batches_processed = 0
        self._total_requests_processed = 0
        self._avg_batch_size = 0.0
        self._total_collect_time_ms = 0.0
        self._total_process_time_ms = 0.0

    async def collect_batch(self) -> list[TranslationRequest]:
        """Collect a batch of requests for processing.

        Returns:
            List of requests to process together (may be empty)
        """
        batch: list[TranslationRequest] = []

        # Get first request (blocking with timeout)
        first_request = await self.queue.get(timeout=1.0)
        if first_request is None:
            return []

        batch.append(first_request)
        config = TIER_CONFIGS[first_request.tier]
        batch_tier = first_request.tier

        # Determine effective batch size
        if self.adaptive_sizing:
            # Scale batch size based on queue depth
            queue_size = self.queue.qsize()
            effective_max = min(
                config.max_batch_size,
                max(config.min_batch_size, queue_size + 1),
            )
        else:
            effective_max = config.max_batch_size

        # Collect more requests
        start_time = time.time()
        max_wait_sec = config.max_wait_ms / 1000.0

        while len(batch) < effective_max:
            elapsed = time.time() - start_time
            remaining = max_wait_sec - elapsed

            if remaining <= 0:
                break

            # Check if we have min batch and higher priority waiting
            if len(batch) >= config.min_batch_size:
                next_priority = await self.queue.peek_priority()
                if next_priority is not None:
                    # Lower (more negative) priority = more important
                    current_priority = first_request.get_priority()
                    # If next request is significantly higher priority, process current batch
                    if next_priority < current_priority - 1:
                        logger.debug(
                            "priority_interruption",
                            batch_size=len(batch),
                            batch_tier=batch_tier.value,
                            next_priority=next_priority,
                        )
                        break

            # Try to get another request (non-blocking with short timeout)
            next_request = await self.queue.get(timeout=min(remaining, 0.01))
            if next_request is None:
                # No more requests available
                if len(batch) >= config.min_batch_size or remaining <= 0:
                    break
                # Wait a bit more for min batch
                await asyncio.sleep(0.005)
                continue

            # Only batch requests with same language pair
            if (
                next_request.source_lang == first_request.source_lang
                and next_request.target_lang == first_request.target_lang
            ):
                batch.append(next_request)
            else:
                # Different language pair - put back and process current batch
                await self.queue.put(next_request)
                break

        return batch

    async def process_batch(self, batch: list[TranslationRequest]) -> BatchResult:
        """Process a batch and return results.

        Args:
            batch: List of requests to process

        Returns:
            BatchResult with translations and metrics

        Raises:
            ValueError: If batch is empty
        """
        if not batch:
            raise ValueError("Cannot process empty batch")

        collect_end = time.time()
        collect_start = batch[0].timestamp

        # Extract texts for translation
        texts = [req.text for req in batch]
        source_lang = batch[0].source_lang
        target_lang = batch[0].target_lang

        # Count tiers in batch
        tier_breakdown: dict[str, int] = {}
        for req in batch:
            tier_breakdown[req.tier.value] = tier_breakdown.get(req.tier.value, 0) + 1

        # Call processor (Modal MT service)
        process_start = time.time()
        translations = await self.processor.translate_batch(
            texts=texts,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        process_end = time.time()

        # Build result
        result = BatchResult(
            requests=batch,
            translations=translations,
            batch_size=len(batch),
            collect_time_ms=(collect_end - collect_start) * 1000,
            process_time_ms=(process_end - process_start) * 1000,
            total_time_ms=(process_end - collect_start) * 1000,
            tier_breakdown=tier_breakdown,
        )

        # Update metrics
        self._batches_processed += 1
        self._total_requests_processed += len(batch)
        self._avg_batch_size = self._total_requests_processed / self._batches_processed
        self._total_collect_time_ms += result.collect_time_ms
        self._total_process_time_ms += result.process_time_ms

        logger.info(
            "batch_processed",
            batch_size=len(batch),
            collect_ms=round(result.collect_time_ms, 2),
            process_ms=round(result.process_time_ms, 2),
            total_ms=round(result.total_time_ms, 2),
            tiers=tier_breakdown,
        )

        return result

    async def collect_and_process(self) -> BatchResult | None:
        """Collect a batch and process it.

        Returns:
            BatchResult or None if no requests available
        """
        batch = await self.collect_batch()
        if not batch:
            return None

        try:
            result = await self.process_batch(batch)

            # Distribute results to waiting futures
            for request, translation in zip(result.requests, result.translations, strict=True):
                if not request.future.done():
                    request.future.set_result(
                        {
                            "translation": translation,
                            "source_lang": request.source_lang,
                            "target_lang": request.target_lang,
                            "latency_ms": result.total_time_ms,
                            "batch_size": result.batch_size,
                            "request_id": request.request_id,
                        }
                    )

            return result

        except Exception as e:
            logger.error("batch_processing_failed", error=str(e), batch_size=len(batch))
            # Fail all requests in batch
            for request in batch:
                if not request.future.done():
                    request.future.set_exception(e)
            raise

    def get_metrics(self) -> dict[str, Any]:
        """Get batcher metrics.

        Returns:
            Dictionary with batcher statistics
        """
        return {
            "batches_processed": self._batches_processed,
            "total_requests_processed": self._total_requests_processed,
            "avg_batch_size": round(self._avg_batch_size, 2),
            "avg_collect_time_ms": (
                round(self._total_collect_time_ms / self._batches_processed, 2)
                if self._batches_processed > 0
                else 0
            ),
            "avg_process_time_ms": (
                round(self._total_process_time_ms / self._batches_processed, 2)
                if self._batches_processed > 0
                else 0
            ),
        }

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self._batches_processed = 0
        self._total_requests_processed = 0
        self._avg_batch_size = 0.0
        self._total_collect_time_ms = 0.0
        self._total_process_time_ms = 0.0
