import copy
from datetime import datetime, timezone

import pytest

from moss import physics as ph
from moss.state import new_state

T0 = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)


def make_state(hunger=0.5, energy=0.5, bowl=0):
    s = new_state("Moss", T0)
    s["drives"] = {"hunger": hunger, "energy": energy}
    s["bowl"]["commits"] = bowl
    return s


def test_night_window_wraps_midnight():
    assert ph.is_night(23) and ph.is_night(3) and ph.is_night(0)
    assert ph.is_night(22) and ph.is_night(6)
    assert not ph.is_night(7) and not ph.is_night(12) and not ph.is_night(21)


def test_fill_bowl_accumulates():
    s = ph.fill_bowl(make_state(), 3)
    s = ph.fill_bowl(s, 2)
    assert s["bowl"]["commits"] == 5


def test_eat_consumes_the_whole_bowl_and_soothes():
    s = ph.apply_action(make_state(hunger=0.9, bowl=3), "eat")
    assert s["drives"]["hunger"] == pytest.approx(0.30)
    assert s["bowl"]["commits"] == 0
    assert s["stats"]["commits_eaten"] == 3


def test_eat_satiety_never_goes_negative():
    s = ph.apply_action(make_state(hunger=0.1, bowl=2), "eat")
    assert s["drives"]["hunger"] == 0.0


def test_eat_from_empty_bowl_is_refused_by_physics_too():
    with pytest.raises(ValueError):
        ph.apply_action(make_state(hunger=0.9, bowl=0), "eat")


def test_sleep_tops_up_but_never_to_perfection():
    assert ph.apply_action(make_state(energy=0.2), "sleep")["drives"]["energy"] == ph.SLEEP_RESTORES_TO
    assert ph.apply_action(make_state(energy=0.9), "sleep")["drives"]["energy"] == 0.9


def test_play_costs_energy():
    assert ph.apply_action(make_state(energy=0.8), "play")["drives"]["energy"] == pytest.approx(0.65)


def test_sulk_increments_the_grievance_count():
    assert ph.apply_action(make_state(), "sulk")["stats"]["sulks"] == 1


def test_apply_action_rejects_nonsense():
    with pytest.raises(ValueError):
        ph.apply_action(make_state(), "feast")


def test_actions_are_pure_original_untouched():
    s = make_state(hunger=0.9, bowl=3)
    snapshot = copy.deepcopy(s)
    ph.apply_action(s, "eat")
    assert s == snapshot