"""A sliding-window rate limit, in memory.

Ticker search and the chart cost one Yahoo round-trip per call, so they get a
ceiling. One uvicorn process serves everything, so a dict is the whole store.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

DEFAULT_LIMIT = 30
DEFAULT_WINDOW = 60.0

_hits: dict[str, deque[float]] = defaultdict(deque)


def allow(
    key: str,
    limit: int = DEFAULT_LIMIT,
    window: float = DEFAULT_WINDOW,
    now: float | None = None,
) -> bool:
    """Record a call for `key` and say whether it is within the ceiling."""
    now = time.monotonic() if now is None else now
    hits = _hits[key]
    while hits and hits[0] <= now - window:
        hits.popleft()
    if len(hits) >= limit:
        return False
    hits.append(now)
    return True


def retry_after(
    key: str, window: float = DEFAULT_WINDOW, now: float | None = None
) -> int:
    """Seconds until the oldest call in the window falls out of it."""
    now = time.monotonic() if now is None else now
    hits = _hits.get(key)
    if not hits:
        return int(window)
    return max(1, int(hits[0] + window - now) + 1)


def reset() -> None:
    _hits.clear()
