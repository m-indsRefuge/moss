"""The composed creature. No disk, no wall time - pure worlds."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from moss import physics as ph
from moss.brain import BrainReply, LLMBrain, ReflexBrain, StubLLM
from moss.clock import SimClock
from moss.policy import Decision, Scene, fallback
from moss.senses import FixtureSenses, Observation
from moss.state import new_state
from moss.tick import tick

UTC = timezone.utc
T0 = datetime(2025, 1, 1, 9, 0, tzinfo=UTC)
DAY = Scene(is_night=False, hours_quiet=0.0)

PERFECT_EAT = ("THOUGHT: the bowl calls\nACTION: eat\nMOOD: smug\n"
               "DIARY: eaten\nWISH: moar")


def make_state(hunger=0.35, energy=0.90, bowl=0):
    s = new_state("Moss", T0)
    s["drives"] = {"hunger": hunger, "energy": energy}
    s["bowl"]["commits"] = bowl
    return s


# -- purity & the timeline -----------------------------------------

def test_tick_never_touches_the_callers_brain():
    s = make_state()
    snapshot = copy.deepcopy(s)
    tick(s, SimClock(T0), FixtureSenses([{"new_commits": 0}]), ReflexBrain())
    assert s == snapshot


def test_last_tick_is_stamped_to_now():
    clock = SimClock(T0)
    clock.advance(hours=5)
    r = tick(make_state(), clock, FixtureSenses([{"new_commits": 0}]), ReflexBrain())
    assert r.state["last_tick"] == clock.now().isoformat()


def test_first_breath_has_zero_decay_and_the_ladder_answers():
    r = tick(make_state(), SimClock(T0),
             FixtureSenses([{"new_commits": 0}]), ReflexBrain())
    assert r.state["drives"]["hunger"] == 0.35        # no time, no decay
    assert r.reply.decision.action == "play"          # rested, fed, day: potter


# -- ordering guarantees --------------------------------------------

def test_bowl_fills_before_the_brain_is_asked():
    stub = StubLLM([PERFECT_EAT])
    clock = SimClock(T0)
    clock.advance(hours=1)
    tick(make_state(), clock, FixtureSenses([{"new_commits": 3}]), LLMBrain(stub))
    assert "bowl holds 3" in stub.prompts[0]


class SpySenses:
    def __init__(self):
        self.calls = []

    def observe(self, now, last_tick):
        self.calls.append((now, last_tick))
        return Observation(new_commits=0, last_commit_at=None)


def test_senses_count_against_the_closed_tick_not_the_new_one():
    spy, clock = SpySenses(), SimClock(T0)
    clock.advance(hours=6)
    tick(make_state(), clock, spy, ReflexBrain())
    now_seen, last_tick_seen = spy.calls[0]
    assert last_tick_seen == T0            # the tick that CLOSED
    assert now_seen == clock.now()         # the moment being lived


# -- a perfect tick, end to end --------------------------------------

def test_perfect_eat_tick_end_to_end():
    stub = StubLLM([PERFECT_EAT])
    clock = SimClock(T0)
    clock.advance(hours=1)
    r = tick(make_state(hunger=0.9), clock,
             FixtureSenses([{"new_commits": 3}]), LLMBrain(stub))
    assert r.reply.decision.action == "eat"
    # order is decay-then-eat: one hour of hunger, then three commits eaten
    expected = 0.9 + ph.HUNGER_RATE - 3 * ph.SATIETY_PER_COMMIT
    assert r.state["drives"]["hunger"] == pytest.approx(expected)
    assert r.state["bowl"]["commits"] == 0
    assert r.state["stats"]["commits_eaten"] == 3
    assert r.state["mood"] == "smug"                   # expression channel
    assert r.state["wish"] == "moar"
    assert r.state["diary"] == ["eaten"]
    assert r.filled == 3 and r.ate == 3
    assert not r.reply.used_fallback


# -- the final veto ---------------------------------------------------

class RogueBrain:
    """A pluggable brain that proposes nonsense. The pet survives it."""

    def decide(self, state, scene):
        return BrainReply(Decision(action="feast", diary="FEAST"), 1, False)


def test_rogue_brain_is_vetoed_into_reflexes():
    # pre-state: the veto substitutes the ladder BEFORE physics applies,
    # so the expected decision is the ladder over the PRE-tick state
    # (which tick must not mutate - proven by the first test above).
    pre = make_state(hunger=0.9, bowl=2)
    r = tick(pre, SimClock(T0), FixtureSenses([]), RogueBrain())
    assert r.reply.used_fallback
    assert r.reply.decision == fallback(pre, DAY)
    assert r.reply.decision.action in ("eat", "sleep", "play", "sulk")
    assert "FEAST" not in "".join(r.state["diary"])


# -- the expression channel's edge cases ------------------------------

def test_empty_mood_preserves_the_current_mood():
    stub = StubLLM(["ACTION: play\nMOOD:\nDIARY: x\nWISH: none"])
    r = tick(make_state(energy=0.8), SimClock(T0), FixtureSenses([]), LLMBrain(stub))
    assert r.reply.decision.action == "play"
    assert r.state["mood"] == "content"        # unchanged


def test_empty_diary_line_is_not_recorded():
    stub = StubLLM(["ACTION: play\nMOOD: happy\nDIARY:   \nWISH: none"])
    r = tick(make_state(energy=0.8), SimClock(T0), FixtureSenses([]), LLMBrain(stub))
    assert r.state["diary"] == []


def test_wish_is_set_then_cleared():
    world = FixtureSenses([])
    clock, s = SimClock(T0), make_state(energy=0.9)
    clock.advance(hours=1)
    s = tick(s, clock, world, LLMBrain(
        StubLLM(["ACTION: play\nMOOD: playful\nDIARY: d1\nWISH: a refactor"]))).state
    assert s["wish"] == "a refactor"
    clock.advance(hours=1)
    s = tick(s, clock, world, LLMBrain(
        StubLLM(["ACTION: play\nMOOD: playful\nDIARY: d2\nWISH: none"]))).state
    assert s["wish"] is None


# -- harness bookkeeping ----------------------------------------------

def test_longest_neglect_grows_in_whole_days():
    clock, s = SimClock(T0), make_state()
    clock.advance(hours=50)
    r = tick(s, clock, FixtureSenses([{"new_commits": 0}]), ReflexBrain())
    assert r.state["stats"]["longest_neglect_days"] == 2


def test_longest_neglect_never_shrinks():
    clock, s = SimClock(T0), make_state()
    clock.advance(hours=50)
    s = tick(s, clock, FixtureSenses([{"new_commits": 0}]), ReflexBrain()).state
    clock.advance(hours=1)
    s = tick(s, clock, FixtureSenses([]), ReflexBrain()).state
    assert s["stats"]["longest_neglect_days"] == 2


# -- the crown: the neglect scenario, end to end ----------------------

def test_neglect_scenario_from_the_fixture_file():
    """The scaffolded fixture, lived through: feed, 10-day silence, feast."""
    scenario = json.loads(
        (Path(__file__).parent.parent / "fixtures" / "scenarios" / "neglect.json")
        .read_text(encoding="utf-8"))

    clock, senses = SimClock(T0), FixtureSenses(scenario)
    s = new_state("Moss", clock.now())
    actions = []
    for _step in scenario:
        clock.advance(hours=_step["advance_hours"])
        r = tick(s, clock, senses, ReflexBrain())
        s = r.state
        actions.append(r.reply.decision.action)

    assert actions == ["eat", "sleep", "eat"]
    assert s["drives"]["hunger"] == 0.0                       # feast saturates
    assert s["drives"]["energy"] == pytest.approx(0.85 - 0.006)
    assert s["bowl"]["commits"] == 0
    assert s["stats"]["commits_eaten"] == 14                  # 3 + 11
    assert s["stats"]["sulks"] == 0                           # night won the arg
    assert s["stats"]["longest_neglect_days"] == 10           # 240h of silence
    assert len(s["diary"]) == 3