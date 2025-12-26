"""Batch Translation Service with Tier-based Priority Queue.

This module provides an intelligent batch processing system for the Modal MT
service that optimizes GPU utilization, reduces cost by ~87%, and provides
tier-based prioritization for different subscription levels.

Usage:
    from app.services.batch import BatchTranslationService, UserTier

    # Create and start service
    service = BatchTranslationService()
    await service.start()

    # Submit translation request
    result = await service.translate(
        text="Hello world",
        source_lang="en",
        target_lang="zh",
        user_id="user123",
        tier=UserTier.BASIC,
    )
    # result = {"translation": "...", "latency_ms": ..., "batch_size": ...}

    # Get metrics
    metrics = service.get_metrics()

    # Shutdown
    await service.stop()

Performance targets:
- Free:       p95 < 250ms
- Basic:      p95 < 200ms
- Pro:        p95 < 170ms
- Enterprise: p95 < 140ms
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.services.batch.batcher import BatchResult, SmartBatcher
from app.services.batch.config import TIER_CONFIGS, TierConfig, UserTier, get_tier_config
from app.services.batch.metrics import BatchMetricsCollector, LatencyMetrics, SLAStatus
from app.services.batch.processor import BatchProcessor, TranslationError
from app.services.batch.queue import TranslationQueue, TranslationRequest

logger = structlog.get_logger(__name__)

__all__ = [
    # Main service
    "BatchTranslationService",
    # Config
    "UserTier",
    "TierConfig",
    "TIER_CONFIGS",
    "get_tier_config",
    # Queue
    "TranslationQueue",
    "TranslationRequest",
    # Batcher
    "SmartBatcher",
    "BatchResult",
    # Processor
    "BatchProcessor",
    "TranslationError",
    # Metrics
    "BatchMetricsCollector",
    "LatencyMetrics",
    "SLAStatus",
]


class BatchTranslationService:
    """High-level batch translation service.

    Manages queue, batcher, processor, and worker lifecycle.
    Provides a simple interface for submitting translation requests
    that are automatically batched for efficient GPU utilization.
    """

    def __init__(
        self,
        modal_endpoint: str | None = None,
        num_workers: int = 2,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ):
        """Initialize the batch translation service.

        Args:
            modal_endpoint: Modal MT service endpoint URL (uses default if None)
            num_workers: Number of worker tasks processing batches
            timeout_seconds: Request timeout for Modal calls
            max_retries: Maximum retries for failed requests
        """
        self.num_workers = num_workers

        # Core components
        self.queue = TranslationQueue()
        self.processor = BatchProcessor(
            modal_endpoint=modal_endpoint,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        self.batcher = SmartBatcher(self.queue, self.processor)
        self.metrics = BatchMetricsCollector()

        # Worker management
        self._workers: list[asyncio.Task[None]] = []
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the batch processing workers.

        Creates worker tasks that continuously process batches from the queue.
        """
        if self._running:
            logger.warning("batch_service_already_running")
            return

        self._running = True
        self._shutdown_event.clear()

        # Start worker tasks
        for i in range(self.num_workers):
            task = asyncio.create_task(
                self._worker_loop(worker_id=i),
                name=f"batch-worker-{i}",
            )
            self._workers.append(task)

        logger.info(
            "batch_service_started",
            num_workers=self.num_workers,
            modal_endpoint=self.processor.modal_endpoint,
        )

    async def stop(self, timeout: float = 5.0) -> None:
        """Stop all workers gracefully.

        Args:
            timeout: Maximum seconds to wait for workers to finish
        """
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # Wait for workers to finish current work
        if self._workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("batch_workers_timeout", timeout=timeout)
                # Force cancel
                for task in self._workers:
                    task.cancel()
                await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()

        # Close processor
        await self.processor.close()

        logger.info("batch_service_stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop for processing batches.

        Args:
            worker_id: Identifier for this worker
        """
        logger.debug("batch_worker_started", worker_id=worker_id)

        while self._running:
            try:
                result = await self.batcher.collect_and_process()

                if result:
                    # Record metrics for each request
                    queue_depth = self.queue.qsize()
                    for request in result.requests:
                        self.metrics.record_request(
                            tier=request.tier,
                            latency_ms=result.total_time_ms,
                            batch_size=result.batch_size,
                            queue_depth=queue_depth,
                        )
                    self.metrics.record_batch(result.batch_size)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "batch_worker_error",
                    worker_id=worker_id,
                    error=str(e),
                )
                # Brief pause before retrying
                await asyncio.sleep(0.1)

        logger.debug("batch_worker_stopped", worker_id=worker_id)

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        user_id: str,
        tier: UserTier | str,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """Submit a translation request.

        The request will be batched with other requests for efficient
        GPU utilization. Higher tier users receive priority processing.

        Args:
            text: Text to translate
            source_lang: Source language code (ISO 639-1)
            target_lang: Target language code (ISO 639-1)
            user_id: User ID for tracking
            tier: User subscription tier
            timeout: Maximum seconds to wait for result

        Returns:
            Dictionary with:
                - translation: Translated text
                - source_lang: Source language
                - target_lang: Target language
                - latency_ms: Total latency
                - batch_size: Size of batch this was processed in
                - request_id: Unique request ID

        Raises:
            asyncio.TimeoutError: If translation takes too long
            TranslationError: If translation fails
            RuntimeError: If service is not running
        """
        if not self._running:
            raise RuntimeError("BatchTranslationService is not running. Call start() first.")

        # Normalize tier
        if isinstance(tier, str):
            try:
                tier = UserTier(tier.lower())
            except ValueError:
                tier = UserTier.FREE

        # Create request
        request = TranslationRequest(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            user_id=user_id,
            tier=tier,
        )

        # Submit to queue
        await self.queue.put(request)

        # Wait for result
        try:
            result = await asyncio.wait_for(request.future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(
                "translation_timeout",
                request_id=request.request_id,
                user_id=user_id,
                tier=tier.value,
                timeout=timeout,
            )
            raise asyncio.TimeoutError(f"Translation timed out after {timeout}s")

    async def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        user_id: str,
        tier: UserTier | str,
        timeout: float = 10.0,
    ) -> list[dict[str, Any]]:
        """Submit multiple translation requests.

        Each text is submitted as a separate request but they may be
        batched together for processing.

        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            user_id: User ID for tracking
            tier: User subscription tier
            timeout: Maximum seconds to wait for all results

        Returns:
            List of result dictionaries (same order as input texts)

        Raises:
            asyncio.TimeoutError: If any translation takes too long
            TranslationError: If any translation fails
        """
        if not texts:
            return []

        # Submit all requests concurrently
        tasks = [
            self.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                user_id=user_id,
                tier=tier,
                timeout=timeout,
            )
            for text in texts
        ]

        # Wait for all results
        results = await asyncio.gather(*tasks)
        return list(results)

    async def health_check(self) -> dict[str, Any]:
        """Check service health.

        Returns:
            Dictionary with service health status
        """
        modal_health = await self.processor.health_check()

        return {
            "status": (
                "healthy"
                if self._running and modal_health.get("status") == "healthy"
                else "unhealthy"
            ),
            "running": self._running,
            "workers_active": len([w for w in self._workers if not w.done()]),
            "queue_size": self.queue.qsize(),
            "modal_service": modal_health,
        }

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive service metrics.

        Returns:
            Dictionary with all metrics from queue, batcher, processor, and metrics collector
        """
        return {
            "service": {
                "running": self._running,
                "workers_active": len([w for w in self._workers if not w.done()]),
            },
            "queue": self.queue.get_metrics(),
            "batcher": self.batcher.get_metrics(),
            "processor": self.processor.get_metrics(),
            "performance": self.metrics.get_summary(),
            "sla": {
                k: {"met": v.sla_met, "target": v.target_ms, "actual_p95": v.actual_p95_ms}
                for k, v in self.metrics.check_sla().items()
            },
        }

    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        self.queue.reset_metrics()
        self.batcher.reset_metrics()
        self.processor.reset_metrics()
        self.metrics.reset()

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running


# Singleton instance for application-wide use
_service_instance: BatchTranslationService | None = None


async def get_batch_service() -> BatchTranslationService:
    """Get or create the batch translation service singleton.

    Returns:
        BatchTranslationService instance
    """
    global _service_instance

    if _service_instance is None:
        _service_instance = BatchTranslationService()
        await _service_instance.start()

    return _service_instance


async def shutdown_batch_service() -> None:
    """Shutdown the batch translation service singleton."""
    global _service_instance

    if _service_instance is not None:
        await _service_instance.stop()
        _service_instance = None
