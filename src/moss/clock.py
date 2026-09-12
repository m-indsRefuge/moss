"""Moss's relationship with time.

THE LAW: no module outside this file may query wall time. Time is a
dependency, injected from above. Production gets RealClock; tests and
simulation get SimClock, where 100 days pass in microseconds.

(Enforced by tests/test_architecture.py - architecture as a test.)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

UTC = timezone.utc


class Clock(Protocol):
    """Anything that can answer 'what time is it?'."""

    def now(self) -> datetime: ...


class RealClock:
    """Wall time. Always timezone-aware UTC."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)


class SimClock:
    """A clock you control. It holds perfectly still until you advance it."""

    def __init__(self, start: datetime | None = None) -> None:
        self._t = start if start is not None else datetime(2025, 1, 1, 9, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._t

    def advance(self, **delta: int) -> None:
        """advance(hours=240, minutes=3) - kwargs mirror timedelta."""
        self._t += timedelta(**delta)