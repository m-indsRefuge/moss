import copy
import json
from datetime import datetime, timezone

import pytest

from moss import state
from moss.state import (
    DIARY_LIMIT,
    CorruptStateError,
    StateError,
    load,
    new_state,
    record_diary,
    save,
    validate,
)

T0 = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)


# -- hatching & roundtrip -----------------------------------------

def test_new_state_is_valid_by_construction():
    s = new_state("Moss", T0)
    validate(s)
    assert s["drives"] == {"hunger": 0.35, "energy": 0.90}
    assert s["stats"]["commits_eaten"] == 0
    assert s["diary"] == []


def test_save_then_load_roundtrips(tmp_path):
    s = record_diary(new_state("Moss", T0), "first words")
    p = tmp_path / "moss.state.json"
    save(p, s)
    assert load(p) == s


def test_missing_brain_loads_as_none(tmp_path):
    assert load(tmp_path / "moss.state.json") is None


# -- atomicity: we cannot kill -9 mid-write in a test, so we test
#    the GUARANTEES that make a mid-write kill survivable ----------

def test_repeated_saves_never_yield_unreadable_file(tmp_path):
    p = tmp_path / "moss.state.json"
    save(p, new_state("Moss", T0))
    for i in range(50):
        s = record_diary(load(p), f"entry {i}")
        save(p, s)
        assert load(p)["diary"][-1] == f"entry {i}"


def test_crashed_save_leaves_debris_but_brain_intact(tmp_path):
    p = tmp_path / "moss.state.json"
    save(p, new_state("Moss", T0))
    # stage the wreckage of a save that died mid-write
    (tmp_path / "moss.state.json.tmp").write_text('{"half-wr', encoding="utf-8")
    assert load(p) is not None                           # the real brain reads fine
    assert not (tmp_path / "moss.state.json.tmp").exists()   # debris swept up


def test_corrupt_brain_raises_loud_and_is_never_reset(tmp_path):
    p = tmp_path / "moss.state.json"
    p.write_text("not json {{{", encoding="utf-8")
    with pytest.raises(CorruptStateError):
        load(p)
    assert p.read_text(encoding="utf-8") == "not json {{{"   # we did NOT overwrite it


# -- validation: the trust boundary -------------------------------

def test_drive_out_of_range_is_rejected():
    s = new_state("Moss", T0)
    s["drives"]["hunger"] = 1.5
    with pytest.raises(StateError):
        validate(s)


def test_bool_drive_is_rejected():
    s = new_state("Moss", T0)
    s["drives"]["energy"] = True   # bool IS an int in Python; guard anyway
    with pytest.raises(StateError):
        validate(s)


def test_mood_is_free_expression_not_a_fixed_enum():
    s = new_state("Moss", T0)
    s["mood"] = "ominously moist"   # drives are constrained; personality is not
    validate(s)                     # no exception = accepted


def test_oversized_mood_is_rejected():
    s = new_state("Moss", T0)
    s["mood"] = "x" * 200
    with pytest.raises(StateError):
        validate(s)


def test_naive_last_tick_is_rejected():
    s = new_state("Moss", T0)
    s["last_tick"] = datetime(2025, 1, 1, 9, 0).isoformat()   # no tzinfo
    with pytest.raises(StateError):
        validate(s)


def test_z_suffix_timestamps_still_parse():
    s = new_state("Moss", T0)
    s["last_tick"] = "2025-01-01T09:00:00Z"   # hand-edited style; must not crash
    validate(s)


# -- versioning: refuse the future, walk up the past --------------

def test_load_refuses_a_brain_from_a_newer_moss(tmp_path):
    p = tmp_path / "moss.state.json"
    s = new_state("Moss", T0)
    s["v"] = 99
    p.write_text(json.dumps(s), encoding="utf-8")   # raw write: save() would reject it
    with pytest.raises(CorruptStateError, match="NEWER"):
        load(p)


def test_migration_walk_upgrades_old_brains(tmp_path, monkeypatch):
    p = tmp_path / "moss.state.json"
    p.write_text(json.dumps(new_state("Moss", T0)), encoding="utf-8")   # a v1 brain
    # prove the MECHANISM before we ever need it: pretend v2 exists
    monkeypatch.setattr(state, "SCHEMA_VERSION", 2)
    monkeypatch.setitem(state._MIGRATIONS, 1, lambda s: {**s, "v": 2})
    assert load(p)["v"] == 2


# -- memory --------------------------------------------------------

def test_diary_is_a_ring_buffer():
    s = new_state("Moss", T0)
    for i in range(30):
        s = record_diary(s, f"day {i}")
    assert len(s["diary"]) == DIARY_LIMIT
    assert s["diary"][-1] == "day 29"
    assert s["diary"][0] == "day 18"