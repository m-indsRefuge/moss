import dataclasses
from datetime import datetime, timezone

import pytest

from moss.policy import Decision, Scene, fallback, is_legal
from moss.state import new_state

T0 = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
DAY = Scene(is_night=False)
NIGHT = Scene(is_night=True)


def make_state(hunger=0.5, energy=0.5, bowl=0):
    s = new_state("Moss", T0)
    s["drives"] = {"hunger": hunger, "energy": energy}
    s["bowl"]["commits"] = bowl
    return s


# -- legality: the veto -------------------------------------------

def test_eat_with_empty_bowl_is_illegal():
    ok, why = is_legal("eat", make_state(hunger=0.9, bowl=0), DAY)
    assert not ok and "bowl" in why


def test_eat_when_full_is_illegal():
    ok, why = is_legal("eat", make_state(hunger=0.10, bowl=3), DAY)
    assert not ok and "hungry" in why


def test_eat_hungry_with_food_is_legal():
    ok, _ = is_legal("eat", make_state(hunger=0.9, bowl=3), DAY)
    assert ok


def test_sleep_at_high_noon_is_illegal():
    ok, why = is_legal("sleep", make_state(energy=0.9), DAY)
    assert not ok and "awake" in why


def test_sleep_is_legal_when_tired():
    ok, _ = is_legal("sleep", make_state(energy=0.2), DAY)
    assert ok


def test_sleep_is_legal_at_night_even_when_wide_awake():
    ok, _ = is_legal("sleep", make_state(energy=0.9), NIGHT)
    assert ok


def test_play_when_exhausted_is_illegal():
    ok, why = is_legal("play", make_state(energy=0.2), DAY)
    assert not ok and "tired" in why


def test_play_with_energy_is_legal():
    ok, _ = is_legal("play", make_state(energy=0.8), DAY)
    assert ok


def test_sulk_needs_no_permission():
    ok, _ = is_legal("sulk", make_state(energy=0.0, hunger=1.0, bowl=0), DAY)
    assert ok


def test_unknown_action_is_illegal():
    ok, why = is_legal("feast", make_state(), DAY)
    assert not ok and "feast" in why


def test_decision_is_frozen():
    d = fallback(make_state(hunger=0.9, bowl=2), DAY)
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.action = "play"


# -- the reflex ladder, rung by rung ------------------------------

@pytest.mark.parametrize(
    "hunger,energy,bowl,scene,quiet,expected",
    [
        (0.90, 0.50, 2, DAY,   0.0, "eat"),    # starving with food
        (0.30, 0.90, 2, NIGHT, 0.0, "sleep"),  # night beats a snack
        (0.30, 0.20, 0, DAY,   0.0, "sleep"),  # exhausted
        (0.50, 0.50, 1, DAY,   0.0, "eat"),    # peckish: snack rung
        (0.20, 0.90, 0, DAY,   0.0, "play"),   # restless
        (0.50, 0.50, 0, DAY,  40.0, "sulk"),   # neglected (and not restless)
        (0.50, 0.50, 0, DAY,   1.0, "play"),   # content and bored -> potter
    ],
    ids=[
        "starving-with-food-eats",
        "night-sleeps-even-with-food-waiting",
        "exhausted-sleeps",
        "peckish-with-food-snacks",
        "restless-plays",
        "neglected-sulks",
        "content-and-bored-potters",
    ],
)
def test_ladder(hunger, energy, bowl, scene, quiet, expected):
    s = make_state(hunger=hunger, energy=energy, bowl=bowl)
    d = fallback(s, Scene(is_night=scene.is_night, hours_quiet=quiet))
    assert d.action == expected


def test_fallback_never_breaks_its_own_laws():
    """Exhaustive grid: every reachable reflex is legal. Preference
    must never stray outside permission."""
    for hunger in (0.0, 0.2, 0.5, 0.8, 1.0):
        for energy in (0.0, 0.1, 0.3, 0.5, 0.8, 1.0):
            for bowl in (0, 3):
                for night in (False, True):
                    for quiet in (0.0, 50.0):
                        s = make_state(hunger=hunger, energy=energy, bowl=bowl)
                        scene = Scene(is_night=night, hours_quiet=quiet)
                        d = fallback(s, scene)
                        ok, why = is_legal(d.action, s, scene)
                        assert ok, f"{d.action} illegal in ({hunger=},{energy=},{bowl=},{night=},{quiet=}): {why}"


def test_fallback_is_deterministic():
    s = make_state(hunger=0.9, bowl=2)
    assert fallback(s, DAY) == fallback(s, DAY)


def test_fallback_voice_rotates_without_randomness():
    a = fallback(make_state(hunger=0.9, bowl=2), DAY)
    b_state = make_state(hunger=0.9, bowl=2)
    b_state["diary"] = ["a previous entry"]
    b = fallback(b_state, DAY)
    assert a.diary != b.diary            # variety...
    assert fallback(b_state, DAY) == b   # ...but pinned, not random


def test_fallback_speaks_through_the_expression_channel():
    d = fallback(make_state(hunger=0.9, bowl=2), DAY)
    assert d.action == "eat"
    assert d.mood == "content"
    assert d.diary                       # a reflex still writes its diary