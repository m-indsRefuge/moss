from datetime import datetime, timezone

import pytest

from moss.state import StateError, load, new_state, save, validate

T0 = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_new_state_hatches_with_an_empty_bowl():
    assert new_state("Moss", T0)["bowl"] == {"commits": 0}


def test_negative_bowl_is_rejected():
    s = new_state("Moss", T0)
    s["bowl"]["commits"] = -1
    with pytest.raises(StateError):
        validate(s)


def test_bowl_bool_is_rejected():
    s = new_state("Moss", T0)
    s["bowl"]["commits"] = True
    with pytest.raises(StateError):
        validate(s)


def test_bowl_survives_a_roundtrip(tmp_path):
    s = new_state("Moss", T0)
    s["bowl"]["commits"] = 7
    p = tmp_path / "moss.state.json"
    save(p, s)
    assert load(p)["bowl"]["commits"] == 7