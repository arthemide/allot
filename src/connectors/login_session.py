"""In-memory state for logins waiting on a second factor.

A login is interactive - the bank asks for a code or an app tap - but HTTP is
stateless, so an attempt in progress is parked here under an opaque id until
its challenge is answered. Credentials live only inside the parked object,
never on disk, and an abandoned attempt is dropped after a short while.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable

# How long an unanswered login may sit before it is forgotten.
TTL_SECONDS = 15 * 60


def _default_factory(login: str, password: str) -> Any:
    # Imported here so woob is only needed when a sync actually runs.
    from src.connectors.woob_bourso import WoobLogin

    return WoobLogin(login, password)


# Overridable in tests: a callable (login, password) -> login object.
factory: Callable[[str, str], Any] = _default_factory


@dataclass
class _Entry:
    attempt: Any
    created: float = field(default_factory=time.monotonic)
    # What the bank reported, kept while new accounts wait for an envelope so
    # the bank is not read twice.
    rows: list | None = None


_entries: dict[str, _Entry] = {}


def _sweep(now: float) -> None:
    for sid in [s for s, e in _entries.items() if now - e.created > TTL_SECONDS]:
        _drop(sid)


def _drop(sid: str) -> None:
    entry = _entries.pop(sid, None)
    if entry is not None:
        try:
            entry.attempt.deinit()
        except Exception:
            pass


def begin(login: str, password: str) -> tuple[str, Any]:
    """Start a login; return its id and the attempt once `start` has run."""
    _sweep(time.monotonic())
    attempt = factory(login, password)
    try:
        attempt.start()
    except Exception:
        attempt.deinit()
        raise
    sid = secrets.token_urlsafe(16)
    _entries[sid] = _Entry(attempt)
    return sid, attempt


def answer(sid: str, value: str) -> Any:
    entry = _entries.get(sid)
    if entry is None:
        raise KeyError(sid)
    entry.attempt.answer(value)
    return entry.attempt


def get(sid: str) -> Any:
    entry = _entries.get(sid)
    return entry.attempt if entry else None


def hold(sid: str, rows: list) -> None:
    """Keep what the bank reported until the user has placed its accounts."""
    _entries[sid].rows = rows


def held(sid: str) -> list | None:
    entry = _entries.get(sid)
    return entry.rows if entry else None


def finish(sid: str) -> None:
    """Drop a login once its sync is done or it has failed."""
    _drop(sid)


def reset() -> None:
    for sid in list(_entries):
        _drop(sid)
