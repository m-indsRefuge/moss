"""Application transactions use the real core and real JSON persistence."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from threading import Event

import pytest

from moss.brain import LLMBrain, ReflexBrain, StubLLM
from moss.clock import SimClock
from moss.runtime import MossRuntime
from moss.senses import FixtureSenses
from moss.state import StateError, load, new_state, save
from moss.tick import tick


def runtime(home, **kwargs):
    return MossRuntime(home, clock=SimClock(), senses=FixtureSenses([]), **kwargs)


def test_open_hatches_only_once_and_returns_immutable_snapshot(tmp_path):
    service = runtime(tmp_path)
    first = service.open()
    path = tmp_path / "moss.state.json"
    before = path.read_bytes()
    assert first.name == "Moss" and first.action == "idle"
    assert first.hunger == 0.35 and first.energy == 0.9
    assert first.diary == () and first.brain_status == "Not run this visit"
    assert service.open() == first
    assert path.read_bytes() == before
    with pytest.raises(FrozenInstanceError):
        first.mood = "invented"


def test_existing_moss_load_is_not_a_tick(tmp_path):
    state = new_state("Fern", SimClock().now())
    state["bowl"]["commits"] = 4
    state["diary"] = ["Remember me"]
    save(tmp_path / "moss.state.json", state)
    view = runtime(tmp_path).open()
    assert (view.name, view.bowl, view.diary) == ("Fern", 4, ("Remember me",))
    assert load(tmp_path / "moss.state.json") == state


def test_tick_is_exactly_core_output_and_persists_before_return(tmp_path):
    clock = SimClock()
    service = MossRuntime(tmp_path, clock=clock, senses=FixtureSenses([{"new_commits": 3}]))
    service.open()
    before = load(service.state_path)
    clock.advance(hours=1)
    expected = tick(before, clock, FixtureSenses([{"new_commits": 3}]), ReflexBrain())
    view = service.live_tick()
    assert load(service.state_path) == expected.state
    assert view.action == "eat" and view.bowl == 0
    assert view.brain_status == "Reflex" and view.diary == tuple(expected.state["diary"])
    assert runtime(tmp_path).open().diary == view.diary


@pytest.mark.parametrize("raw", ['broken {', '{"v":1}', '{"v":999}'])
def test_invalid_state_never_hatches_over_existing_file(tmp_path, raw):
    path = tmp_path / "moss.state.json"
    path.write_text(raw, encoding="utf-8")
    service = runtime(tmp_path)
    for operation in (service.open, service.live_tick):
        with pytest.raises(StateError):
            operation()
        assert path.read_text(encoding="utf-8") == raw


def test_transport_failure_uses_existing_reflex_fallback(tmp_path):
    view = runtime(tmp_path, brain=LLMBrain(StubLLM([]))).live_tick()
    assert view.brain_status == "Reflex fallback"
    assert view.action == "play" and view.diary


def test_llm_public_expression_is_exposed_without_raw_state(tmp_path):
    view = runtime(tmp_path, brain=LLMBrain(StubLLM([
        "ACTION: play\nTHOUGHT: A pebble!\nMOOD: curious\nDIARY: I explored.\nWISH: more pebbles"
    ]))).live_tick()
    assert view.brain_status == "LLM decision"
    assert (view.thought, view.mood, view.wish) == ("A pebble!", "curious", "more pebbles")
    assert not hasattr(view, "state")


def test_save_failure_does_not_publish_or_change_persistent_state(tmp_path, monkeypatch):
    service = runtime(tmp_path)
    service.open()
    before = service.state_path.read_bytes()
    def fail(*args):
        raise OSError("disk failure")
    monkeypatch.setattr("moss.runtime.save", fail)
    with pytest.raises(OSError):
        service.live_tick()
    assert service.state_path.read_bytes() == before


def test_transactions_are_serialized_and_second_load_sees_first_save(tmp_path):
    entered, release, second_requested = Event(), Event(), Event()
    class HeldBrain:
        calls = 0
        def decide(self, state, scene):
            self.calls += 1
            if self.calls == 1:
                entered.set()
                assert release.wait(5)
            return ReflexBrain().decide(state, scene)
    brain = HeldBrain()
    service = runtime(tmp_path, brain=brain)
    service.open()
    def second_tick():
        second_requested.set()
        return service.live_tick()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(service.live_tick)
        try:
            assert entered.wait(5)
            second = pool.submit(second_tick)
            assert second_requested.wait(5)
            assert not second.done() and brain.calls == 1
        finally:
            release.set()
        assert len(first.result().diary) == 1
        assert len(second.result().diary) == 2
    assert len(load(service.state_path)["diary"]) == 2


def test_habitat_projection_distinguishes_lifetime_from_this_visit(tmp_path):
    service = runtime(tmp_path)
    state = new_state("Moss", service.clock.now())
    state["stats"].update(commits_eaten=12, sulks=3, longest_neglect_days=8)
    save(service.state_path, state)
    opened = service.open()
    assert (opened.commits_eaten, opened.sulks, opened.longest_neglect_days) == (12, 3, 8)
    assert not opened.has_tick and opened.last_commit_at == ""
    assert opened.decision_attempts == 0 and not opened.used_fallback
    assert service.brain_label == "Reflex"


def test_habitat_telemetry_comes_from_completed_core_tick(tmp_path):
    clock = SimClock()
    service = MossRuntime(tmp_path, clock=clock, senses=FixtureSenses([{"new_commits": 3}]),
                          brain=LLMBrain(StubLLM([])))
    result = service.live_tick()
    assert result.has_tick and result.commits_arrived == result.commits_eaten_this_tick == 3
    assert result.commits_eaten == 3 and result.sulks == 0
    assert result.decision_attempts == 2 and result.used_fallback
    assert result.last_commit_at == clock.now().isoformat()
    assert result.hours_quiet == 0 and not result.is_night
    reopened = runtime(tmp_path).open()
    assert reopened.commits_eaten == 3 and not reopened.has_tick
    assert reopened.commits_arrived == 0 and reopened.last_commit_at == ""


def test_ambiguous_git_observation_does_not_claim_a_last_commit(tmp_path):
    from moss.senses import GitSenses
    (tmp_path / ".git").write_text("gitdir: nowhere\n", encoding="utf-8")
    result = MossRuntime(tmp_path, clock=SimClock(), senses=GitSenses(tmp_path)).live_tick()
    assert result.has_tick and result.last_commit_at == ""
    assert result.repo_status == "Git unavailable or empty history"
