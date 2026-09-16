"""Pure scheduling cadence for one interactive Moss habitat session."""
from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Protocol

WAKE_MIN_S = 30
WAKE_MAX_S = 90

STEADY_MIN_S = 6 * 60
STEADY_MODE_S = 10 * 60
STEADY_MAX_S = 14 * 60


class RandomSource(Protocol):
    def uniform(self, a: float, b: float) -> float: ...
    def triangular(self, low: float, high: float, mode: float) -> float: ...


@dataclass
class LifecycleCadence:
    rng: RandomSource = field(default_factory=Random)

    def wake_delay_ms(self) -> int:
        return round(self.rng.uniform(WAKE_MIN_S, WAKE_MAX_S) * 1000)

    def steady_delay_ms(self) -> int:
        return round(
            self.rng.triangular(
                STEADY_MIN_S,
                STEADY_MAX_S,
                STEADY_MODE_S,
            )
            * 1000
        )
