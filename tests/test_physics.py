import copy
from datetime import datetime, timedelta, timezone

import pytest

from moss import physics as ph
from moss.state import new_state

T0 = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_zero_elapsed_changes_nothing():
    s = new_state("Moss", T0)
    assert ph.decay(s, timedelta(0)) == s


def test_negative_elapsed_is_ignored_not_punished():
    s = new_state("Moss", T0)
    assert ph.decay(s, timedelta(hours=-5)) == s   # clock skew: be lenient


def test_one_hour_of_time_costs_hunger_and_energy():
    s = new_state("Moss", T0)
    out = ph.decay(s, timedelta(hours=1))
    assert out["drives"]["hunger"] == pytest.approx(s["drives"]["hunger"] + ph.HUNGER_RATE)
    assert out["drives"]["energy"] == pytest.approx(s["drives"]["energy"] - ph.ENERGY_RATE)


def test_a_long_neglect_saturates_the_drives():
    s = new_state("Moss", T0)
    out = ph.decay(s, timedelta(days=365))
    assert out["drives"]["hunger"] == 1.0
    assert out["drives"]["energy"] == 0.0


def test_decay_returns_a_new_brain_and_leaves_the_original_alone():
    s = new_state("Moss", T0)
    snapshot = copy.deepcopy(s)
    out = ph.decay(s, timedelta(hours=10))
    assert s == snapshot
    assert out is not s