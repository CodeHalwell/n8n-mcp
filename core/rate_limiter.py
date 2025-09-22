from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimitExceeded(RuntimeError):
    """Raised when an actor exceeds their allowed request budget."""


class RateLimiter:
    def __init__(self, max_per_minute: int) -> None:
        if max_per_minute <= 0:
            raise ValueError("max_per_minute must be positive")
        self.max_per_minute = max_per_minute
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, actor: str) -> None:
        now = time.time()
        window_start = now - 60.0
        bucket = self._buckets[actor]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= self.max_per_minute:
            raise RateLimitExceeded("rate_limit_exceeded")

        bucket.append(now)
