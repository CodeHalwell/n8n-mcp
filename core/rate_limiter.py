from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
	def __init__(self, max_per_minute: int) -> None:
		self.max_per_minute = max_per_minute
		self._buckets: Dict[str, Deque[float]] = defaultdict(deque)

	def check(self, actor: str) -> None:
		now = time.time()
		window_start = now - 60.0
		bucket = self._buckets[actor]
		while bucket and bucket[0] < window_start:
			bucket.popleft()
		if len(bucket) >= self.max_per_minute:
			raise RuntimeError("rate_limit_exceeded")
		bucket.append(now)