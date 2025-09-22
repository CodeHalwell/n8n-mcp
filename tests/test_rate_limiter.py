from __future__ import annotations

import time

import pytest
from pytest import MonkeyPatch

from core.rate_limiter import RateLimiter, RateLimitExceeded


def test_rate_limiter_allows_within_window(monkeypatch: MonkeyPatch) -> None:
    limiter = RateLimiter(max_per_minute=2)
    limiter.check("actor")
    limiter.check("actor")

    # Move time forward so the window expires and the bucket is drained.
    current = time.time()

    def fake_time() -> float:
        return current

    monkeypatch.setattr(time, "time", lambda: current)
    current += 120
    limiter.check("actor")


def test_rate_limiter_raises_when_exceeded() -> None:
    limiter = RateLimiter(max_per_minute=1)
    limiter.check("actor")
    with pytest.raises(RateLimitExceeded):
        limiter.check("actor")
