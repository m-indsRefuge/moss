"""The loop: decay -> sense -> fill -> decide -> veto -> apply -> remember.

tick() is PURE COMPOSITION: a world in (state, clock, senses, brain),
a TickResult out. No disk I/O, no wall time - both are injected by
cli.py, which is the ONLY place Moss touches reality.

The Brain protocol lives HERE, not in brain.py: interfaces belong to
their consumer. Both ReflexBrain and LLMBrain satisfy it without
knowing it exists - structural typing again.

Order matters in quiet ways:
- the bowl is filled BEFORE the brain is asked, so a brain never
  sees a world where fresh food does not exist yet;
- last_tick is captured BEFORE decay, so senses count commits
  against the tick that CLOSED, not the one being written;
- last_tick is stamped LAST - a tick that dies midway leaves the
  brain file's timeline honest.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Protocol

from moss import physics as ph
from moss.brain import BrainReply
from moss.clock import Clock
from moss.policy import fallback, is_legal
from moss.senses import Observation, Senses, make_scene
from moss.state import parse_ts, record_diary


class Brain(Protocol):
    """Anything that can answer 'what do you do?' with a Decision."""

    def decide(self, state: dict[str, Any], scene: Any) -> BrainReply: ...


@dataclass(frozen=True)
class TickResult:
    """One lived moment: the new brain, plus telemetry for rendering."""

    state: dict[str, Any]
    reply: BrainReply
    scene: Any
    filled: int   # commits delivered to the bowl this tick
    ate: int      # commits actually eaten this tick


def tick(state: dict[str, Any], clock: Clock, senses: Senses, brain: Brain) -> TickResult:
    # One private copy; from here on, mutation is tick's own business
    # and the caller's dict is never touched.
    state = copy.deepcopy(state)
    prev_tick = parse_ts(state["last_tick"])
    now = clock.now()

    # 1. time passes
    state = ph.decay(state, now - prev_tick)

    # 2. the world is observed (against the tick that CLOSED)
    obs = senses.observe(now=now, last_tick=prev_tick)
    scene = make_scene(obs, last_tick=prev_tick, now=now)

    # 3. food arrives
    state = ph.fill_bowl(state, obs.new_commits)

    # 4. the brain proposes
    reply = brain.decide(state, scene)

    # 5. the harness disposes - final veto, independent of the brain's
    #    own policing. A broken pluggable brain degrades to reflexes;
    #    it does not take the pet down with it.
    ok, _why = is_legal(reply.decision.action, state, scene)
    if not ok:
        reply = BrainReply(decision=fallback(state, scene),
                           attempts=reply.attempts, used_fallback=True)
    d = reply.decision

    # 6. physics applies the action (drives + stats ONLY)
    ate_before = state["stats"]["commits_eaten"]
    state = ph.apply_action(state, d.action)
    ate = state["stats"]["commits_eaten"] - ate_before

    # 7. the expression channel (mood, diary, wish - never physics)
    if d.mood is not None:
        state["mood"] = d.mood
    if d.diary:
        state = record_diary(state, d.diary)
    state["wish"] = d.wish

    # 8. harness bookkeeping: the longest silence, in whole days
    neglect_days = int(scene.hours_quiet // 24)
    if neglect_days > state["stats"]["longest_neglect_days"]:
        state["stats"]["longest_neglect_days"] = neglect_days

    # 9. the timeline closes - last of all
    state["last_tick"] = now.isoformat()

    return TickResult(state=state, reply=reply, scene=scene,
                      filled=obs.new_commits, ate=ate)