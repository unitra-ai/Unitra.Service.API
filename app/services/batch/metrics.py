"""Metrics for monitoring batch translation performance.

Key metrics to track:
- Latency by tier (p50, p95, p99)
- Batch size distribution
- Queue depth over time
- Throughput (requests per second)
- SLA compliance
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field

from app.services.batch.config import TIER_CONFIGS, UserTier


@dataclass
class LatencyMetrics:
    """Latency statistics for a tier."""

    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    avg: float = 0.0
    min: float = 0.0
    max: float = 0.0
    count: int = 0


@dataclass
class SLAStatus:
    """SLA compliance status for a tier."""

    tier: str
    target_ms: int
    actual_p95_ms: float
    sla_met: bool
    sample_count: int
    violation_count: int = 0


class BatchMetricsCollector:
    """Collects and aggregates batch translation metrics.

    Thread-safe metrics collection with configurable window size.
    """

    def __init__(self, window_size: int = 1000):
        """Initialize metrics collector.

        Args:
            window_size: Number of recent samples to keep
        """
        self.window_size = window_size

        # Latency tracking by tier
        self._latencies: dict[UserTier, list[float]] = defaultdict(list)

        # Batch size tracking
        self._batch_sizes: list[int] = []

        # Queue depth samples
        self._queue_depths: list[int] = []

        # Timestamps for rate calculation
        self._request_times: list[float] = []

        # SLA violations
        self._sla_violations: dict[UserTier, int] = defaultdict(int)

        # Total counts
        self._total_requests = 0
        self._total_batches = 0

    def record_request(
        self,
        tier: UserTier,
        latency_ms: float,
        batch_size: int,
        queue_depth: int,
    ) -> None:
        """Record a completed request.

        Args:
            tier: User tier
            latency_ms: Total latency in milliseconds
            batch_size: Size of the batch this request was in
            queue_depth: Queue depth when request was processed
        """
        now = time.time()

        # Record latency
        self._latencies[tier].append(latency_ms)
        if len(self._latencies[tier]) > self.window_size:
            self._latencies[tier].pop(0)

        # Check SLA violation
        config = TIER_CONFIGS[tier]
        if latency_ms > config.target_latency_ms * 1.2:  # 20% tolerance
            self._sla_violations[tier] += 1

        # Record batch size
        self._batch_sizes.append(batch_size)
        if len(self._batch_sizes) > self.window_size:
            self._batch_sizes.pop(0)

        # Record queue depth
        self._queue_depths.append(queue_depth)
        if len(self._queue_depths) > self.window_size:
            self._queue_depths.pop(0)

        # Record timestamp
        self._request_times.append(now)
        if len(self._request_times) > self.window_size:
            self._request_times.pop(0)

        self._total_requests += 1

    def record_batch(self, batch_size: int) -> None:
        """Record a processed batch.

        Args:
            batch_size: Number of requests in batch
        """
        self._total_batches += 1

    def get_latency_by_tier(self, tier: UserTier) -> LatencyMetrics:
        """Get latency statistics for a tier.

        Args:
            tier: User tier to get metrics for

        Returns:
            LatencyMetrics with percentiles and counts
        """
        latencies = self._latencies.get(tier, [])
        if not latencies:
            return LatencyMetrics()

        sorted_lat = sorted(latencies)
        n = len(sorted_lat)

        return LatencyMetrics(
            p50=sorted_lat[int(n * 0.50)],
            p95=sorted_lat[int(n * 0.95)] if n >= 20 else sorted_lat[-1],
            p99=sorted_lat[int(n * 0.99)] if n >= 100 else sorted_lat[-1],
            avg=statistics.mean(latencies),
            min=min(latencies),
            max=max(latencies),
            count=n,
        )

    def get_all_tier_latencies(self) -> dict[str, LatencyMetrics]:
        """Get latency metrics for all tiers.

        Returns:
            Dictionary mapping tier name to LatencyMetrics
        """
        return {tier.value: self.get_latency_by_tier(tier) for tier in UserTier}

    def get_batch_size_stats(self) -> dict:
        """Get batch size statistics.

        Returns:
            Dictionary with avg, min, max batch sizes
        """
        if not self._batch_sizes:
            return {"avg": 0.0, "min": 0, "max": 0, "count": 0}

        return {
            "avg": round(statistics.mean(self._batch_sizes), 2),
            "min": min(self._batch_sizes),
            "max": max(self._batch_sizes),
            "count": len(self._batch_sizes),
        }

    def get_queue_depth_stats(self) -> dict:
        """Get queue depth statistics.

        Returns:
            Dictionary with avg, min, max queue depths
        """
        if not self._queue_depths:
            return {"avg": 0.0, "min": 0, "max": 0}

        return {
            "avg": round(statistics.mean(self._queue_depths), 2),
            "min": min(self._queue_depths),
            "max": max(self._queue_depths),
        }

    def get_throughput(self, window_seconds: float = 60.0) -> float:
        """Get requests per second over recent window.

        Args:
            window_seconds: Time window to calculate throughput

        Returns:
            Requests per second
        """
        now = time.time()
        cutoff = now - window_seconds

        recent = [t for t in self._request_times if t > cutoff]
        if len(recent) < 2:
            return 0.0

        duration = recent[-1] - recent[0]
        if duration <= 0:
            return 0.0

        return round(len(recent) / duration, 2)

    def check_sla(self) -> dict[str, SLAStatus]:
        """Check if SLA targets are met for all tiers.

        Returns:
            Dictionary mapping tier name to SLAStatus
        """
        results = {}

        for tier in UserTier:
            config = TIER_CONFIGS[tier]
            metrics = self.get_latency_by_tier(tier)

            # SLA is met if p95 is within 20% of target
            sla_met = (
                metrics.p95 <= config.target_latency_ms * 1.2 if metrics.count > 0 else True
            )

            results[tier.value] = SLAStatus(
                tier=tier.value,
                target_ms=config.target_latency_ms,
                actual_p95_ms=round(metrics.p95, 2),
                sla_met=sla_met,
                sample_count=metrics.count,
                violation_count=self._sla_violations.get(tier, 0),
            )

        return results

    def get_summary(self) -> dict:
        """Get comprehensive metrics summary.

        Returns:
            Dictionary with all metrics
        """
        return {
            "total_requests": self._total_requests,
            "total_batches": self._total_batches,
            "throughput_per_second": self.get_throughput(),
            "batch_sizes": self.get_batch_size_stats(),
            "queue_depth": self.get_queue_depth_stats(),
            "latency_by_tier": {
                tier.value: {
                    "p50": round(m.p50, 2),
                    "p95": round(m.p95, 2),
                    "p99": round(m.p99, 2),
                    "avg": round(m.avg, 2),
                    "count": m.count,
                }
                for tier, m in [
                    (t, self.get_latency_by_tier(t)) for t in UserTier
                ]
                if m.count > 0
            },
            "sla_status": {
                k: {"met": v.sla_met, "target": v.target_ms, "actual_p95": v.actual_p95_ms}
                for k, v in self.check_sla().items()
                if v.sample_count > 0
            },
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._latencies = defaultdict(list)
        self._batch_sizes = []
        self._queue_depths = []
        self._request_times = []
        self._sla_violations = defaultdict(int)
        self._total_requests = 0
        self._total_batches = 0
