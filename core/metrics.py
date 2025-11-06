"""Metrics collection and health monitoring for the MCP server."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Dict, Deque, List, Optional
from dataclasses import dataclass, field, asdict
import threading


@dataclass
class MetricSnapshot:
    """A point-in-time snapshot of a metric."""

    timestamp: float
    value: float


@dataclass
class HealthStatus:
    """Overall health status of the system."""

    status: str  # "healthy", "degraded", "unhealthy"
    checks: Dict[str, Dict[str, Any]]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsCollector:
    """
    Collects and aggregates metrics for monitoring.

    Tracks:
    - Request counts and rates
    - Response times (latency)
    - Error rates
    - Cache hit rates
    - Circuit breaker state changes
    """

    def __init__(self, window_seconds: float = 300.0):
        """
        Initialize metrics collector.

        Args:
            window_seconds: Time window for rate calculations (default: 5 minutes)
        """
        self.window_seconds = window_seconds
        self._lock = threading.Lock()

        # Counters
        self._request_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        # Time series data (for rate calculations)
        self._request_times: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._latency_samples: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=100)
        )

        # Circuit breaker state changes
        self._circuit_breaker_state_changes: List[Dict[str, Any]] = []

        # Start time
        self._start_time = time.time()

    def record_request(self, operation: str, latency_ms: float, error: bool = False) -> None:
        """
        Record a request.

        Args:
            operation: Operation name (e.g., "list_workflows", "create_workflow")
            latency_ms: Request latency in milliseconds
            error: Whether the request resulted in an error
        """
        with self._lock:
            now = time.time()

            # Increment counters
            self._request_counts[operation] += 1
            if error:
                self._error_counts[operation] += 1

            # Record timing
            self._request_times[operation].append(now)
            self._latency_samples[operation].append(latency_ms)

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self._cache_misses += 1

    def record_circuit_breaker_state_change(
        self, service: str, old_state: str, new_state: str
    ) -> None:
        """
        Record a circuit breaker state change.

        Args:
            service: Service name
            old_state: Previous state
            new_state: New state
        """
        with self._lock:
            self._circuit_breaker_state_changes.append(
                {
                    "timestamp": time.time(),
                    "service": service,
                    "old_state": old_state,
                    "new_state": new_state,
                }
            )

    def get_request_rate(self, operation: Optional[str] = None) -> float:
        """
        Calculate requests per second for an operation or all operations.

        Args:
            operation: Optional operation name (None = all operations)

        Returns:
            Requests per second
        """
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            if operation:
                # Rate for specific operation
                times = self._request_times.get(operation, deque())
                recent_requests = sum(1 for t in times if t >= cutoff)
                return recent_requests / self.window_seconds

            # Rate for all operations
            total_requests = 0
            for times in self._request_times.values():
                total_requests += sum(1 for t in times if t >= cutoff)

            return total_requests / self.window_seconds

    def get_error_rate(self, operation: Optional[str] = None) -> float:
        """
        Calculate error rate (errors / total requests).

        Args:
            operation: Optional operation name (None = all operations)

        Returns:
            Error rate between 0.0 and 1.0
        """
        with self._lock:
            if operation:
                total = self._request_counts.get(operation, 0)
                errors = self._error_counts.get(operation, 0)
            else:
                total = sum(self._request_counts.values())
                errors = sum(self._error_counts.values())

            return errors / total if total > 0 else 0.0

    def get_average_latency(self, operation: Optional[str] = None) -> float:
        """
        Calculate average latency in milliseconds.

        Args:
            operation: Optional operation name (None = all operations)

        Returns:
            Average latency in milliseconds
        """
        with self._lock:
            if operation:
                samples = list(self._latency_samples.get(operation, deque()))
            else:
                # All operations
                samples = []
                for operation_samples in self._latency_samples.values():
                    samples.extend(operation_samples)

            return sum(samples) / len(samples) if samples else 0.0

    def get_p95_latency(self, operation: Optional[str] = None) -> float:
        """
        Calculate 95th percentile latency in milliseconds.

        Args:
            operation: Optional operation name (None = all operations)

        Returns:
            P95 latency in milliseconds
        """
        with self._lock:
            if operation:
                samples = list(self._latency_samples.get(operation, deque()))
            else:
                samples = []
                for operation_samples in self._latency_samples.values():
                    samples.extend(operation_samples)

            if not samples:
                return 0.0

            sorted_samples = sorted(samples)
            p95_index = int(len(sorted_samples) * 0.95)
            return sorted_samples[p95_index]

    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Cache hit rate between 0.0 and 1.0
        """
        with self._lock:
            total = self._cache_hits + self._cache_misses
            return self._cache_hits / total if total > 0 else 0.0

    def get_uptime_seconds(self) -> float:
        """
        Get server uptime in seconds.

        Returns:
            Uptime in seconds
        """
        return time.time() - self._start_time

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.

        Returns:
            Dictionary containing all metrics
        """
        with self._lock:
            uptime = self.get_uptime_seconds()

            summary = {
                "uptime_seconds": uptime,
                "uptime_human": self._format_uptime(uptime),
                "requests": {
                    "total": sum(self._request_counts.values()),
                    "by_operation": dict(self._request_counts),
                    "rate_per_second": self.get_request_rate(),
                },
                "errors": {
                    "total": sum(self._error_counts.values()),
                    "by_operation": dict(self._error_counts),
                    "error_rate": self.get_error_rate(),
                },
                "latency": {
                    "average_ms": self.get_average_latency(),
                    "p95_ms": self.get_p95_latency(),
                },
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate": self.get_cache_hit_rate(),
                },
                "circuit_breaker": {
                    "state_changes": len(self._circuit_breaker_state_changes),
                    "recent_changes": self._circuit_breaker_state_changes[-5:],
                },
            }

            return summary

    def check_health(self) -> HealthStatus:
        """
        Perform health checks and return overall status.

        Returns:
            HealthStatus with overall health and individual check results
        """
        checks = {}

        # Check 1: Error rate
        error_rate = self.get_error_rate()
        checks["error_rate"] = {
            "status": "healthy" if error_rate < 0.1 else "unhealthy",
            "value": error_rate,
            "threshold": 0.1,
            "message": f"Error rate: {error_rate:.2%}",
        }

        # Check 2: Request rate (too low might indicate issues)
        request_rate = self.get_request_rate()
        checks["request_rate"] = {
            "status": "healthy",  # Just informational
            "value": request_rate,
            "message": f"Request rate: {request_rate:.2f} req/s",
        }

        # Check 3: Average latency
        avg_latency = self.get_average_latency()
        checks["latency"] = {
            "status": "healthy" if avg_latency < 1000 else "degraded" if avg_latency < 3000 else "unhealthy",
            "value": avg_latency,
            "thresholds": {"warning": 1000, "critical": 3000},
            "message": f"Average latency: {avg_latency:.0f}ms",
        }

        # Check 4: Cache effectiveness
        cache_hit_rate = self.get_cache_hit_rate()
        total_cache_requests = self._cache_hits + self._cache_misses
        if total_cache_requests > 10:  # Only check if we have enough samples
            checks["cache"] = {
                "status": "healthy" if cache_hit_rate > 0.5 else "degraded",
                "value": cache_hit_rate,
                "threshold": 0.5,
                "message": f"Cache hit rate: {cache_hit_rate:.0%}",
            }
        else:
            checks["cache"] = {
                "status": "healthy",
                "message": "Insufficient cache data for evaluation",
            }

        # Determine overall status
        statuses = [check["status"] for check in checks.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return HealthStatus(status=overall_status, checks=checks)

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._request_counts.clear()
            self._error_counts.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._request_times.clear()
            self._latency_samples.clear()
            self._circuit_breaker_state_changes.clear()
            self._start_time = time.time()


# Global metrics collector instance
metrics_collector = MetricsCollector()
