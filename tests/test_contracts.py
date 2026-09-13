"""The executable contract between the Moss core and its UI.

Handoff armor: these tests pin the names, fields, and shapes that
tui.py (and any future renderer) consumes. If a refactor breaks any
of them, the gate goes red BEFORE a UI silently rots. Treat this
file as the source of truth for data shapes; HANDOFF.md just
points here.
"""
import dataclasses
import inspect
from datetime import datetime, timezone

from moss import brain, cli, llm, physics, policy, senses, state
from moss import tick as tick_mod

T0 = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)


def _fields(cls):
    return [f.name for f in dataclasses.fields(cls)]


# -- the records a renderer will display --------------------------

def test_decision_fields():
    assert _fields(policy.Decision) == ["action", "thought", "diary", "mood", "wish"]


def test_scene_fields():
    assert _fields(policy.Scene) == ["new_commits", "hours_quiet", "is_night", "repo_digest"]


def test_observation_fields():
    assert _fields(senses.Observation) == ["new_commits", "last_commit_at", "repo_digest"]


def test_brain_reply_fields():
    assert _fields(brain.BrainReply) == ["decision", "attempts", "used_fallback"]


def test_tick_result_fields():
    assert _fields(tick_mod.TickResult) == ["state", "reply", "scene", "filled", "ate"]


# -- the brain file schema, pinned key by key ----------------------

def test_brain_file_schema_is_pinned():
    s = state.new_state("Moss", T0)
    assert sorted(s) == ["bowl", "diary", "drives", "last_tick", "mood",
                         "name", "stats", "v", "wish"]
    assert sorted(s["drives"]) == ["energy", "hunger"]
    assert sorted(s["stats"]) == ["commits_eaten", "longest_neglect_days", "sulks"]
    assert sorted(s["bowl"]) == ["commits"]


def test_drives_are_floats_in_unit_range_at_birth():
    s = state.new_state("Moss", T0)
    for v in s["drives"].values():
        assert isinstance(v, float) and 0.0 <= v <= 1.0


# -- the composition entry point -----------------------------------

def test_tick_signature_is_stable():
    params = list(inspect.signature(tick_mod.tick).parameters)
    assert params == ["state", "clock", "senses", "brain"]


def test_public_surface_exists():
    # state
    for name in ("load", "save", "validate", "parse_ts", "record_diary",
                 "new_state", "CorruptStateError", "StateError"):
        assert hasattr(state, name), name
    # brains & protocol
    for name in ("build_prompt", "parse_decision", "LLMBrain", "ReflexBrain",
                 "StubLLM", "MAX_ATTEMPTS"):
        assert hasattr(brain, name), name
    # senses
    for name in ("GitSenses", "FixtureSenses", "make_scene", "Observation"):
        assert hasattr(senses, name), name
    # transport
    for name in ("OllamaLLM", "strip_thinking"):
        assert hasattr(llm, name), name
    # console
    for name in ("format_status", "format_tick", "main"):
        assert hasattr(cli, name), name
    # genome constants (simulation UI may surface them)
    for name in ("HUNGER_RATE", "ENERGY_RATE", "SATIETY_PER_COMMIT",
                 "SLEEP_RESTORES_TO", "NIGHT_UTC_START", "NIGHT_UTC_END"):
        assert hasattr(physics, name), name


def test_is_legal_returns_verdict_and_reason():
    s = state.new_state("Moss", T0)
    ok, why = policy.is_legal("sulk", s, policy.Scene())
    assert ok is True and isinstance(why, str)


def test_known_moods_is_the_renderer_vocabulary():
    assert set(policy.KNOWN_MOODS) == {"content", "sleepy", "playful", "sulky"}


def test_reflex_brain_only_speaks_known_moods():
    from moss.policy import Scene, fallback
    for energy in (0.0, 0.2, 0.5, 0.9):
        for night in (False, True):
            s = state.new_state("Moss", T0)
            s["drives"]["energy"] = energy
            d = fallback(s, Scene(is_night=night))
            assert d.mood in policy.KNOWN_MOODS


def test_stub_llm_satisfies_the_transport_protocol():
    stub = brain.StubLLM(["ACTION: play"])
    assert stub.complete("p") == "ACTION: play"   # duck-typed LLM, by design
