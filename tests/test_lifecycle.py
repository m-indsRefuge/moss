from random import Random

from moss.lifecycle import (
    STEADY_MAX_S,
    STEADY_MIN_S,
    STEADY_MODE_S,
    WAKE_MAX_S,
    WAKE_MIN_S,
    LifecycleCadence,
)


class RecordingRng:
    def __init__(self):
        self.calls = []

    def uniform(self, low, high):
        self.calls.append(("uniform", low, high))
        return 42.5

    def triangular(self, low, high, mode):
        self.calls.append(("triangular", low, high, mode))
        return 601.25


def test_cadence_uses_exact_wake_and_steady_distribution_contracts():
    rng = RecordingRng()
    cadence = LifecycleCadence(rng=rng)

    assert cadence.wake_delay_ms() == 42_500
    assert cadence.steady_delay_ms() == 601_250
    assert rng.calls == [
        ("uniform", 30, 90),
        ("triangular", 360, 840, 600),
    ]
    assert (WAKE_MIN_S, WAKE_MAX_S) == (30, 90)
    assert (STEADY_MIN_S, STEADY_MODE_S, STEADY_MAX_S) == (360, 600, 840)


def test_seeded_cadence_is_reproducible_and_bounded():
    left = LifecycleCadence(rng=Random(1234))
    right = LifecycleCadence(rng=Random(1234))

    left_values = [
        left.wake_delay_ms(),
        *[left.steady_delay_ms() for _ in range(100)],
    ]
    right_values = [
        right.wake_delay_ms(),
        *[right.steady_delay_ms() for _ in range(100)],
    ]

    assert left_values == right_values
    assert 30_000 <= left_values[0] <= 90_000
    assert all(360_000 <= value <= 840_000 for value in left_values[1:])
