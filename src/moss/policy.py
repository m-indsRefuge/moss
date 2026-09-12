"""Moss's reflexes - and the shape of a decision.

Three things live here:

1. Decision - the fixed record a brain returns. The rule-based
   fallback produces one today; the LLM brain produces one later.
   The LLM must sign this contract, not invent its own format.
2. is_legal - the harness's veto. The brain PROPOSES; this disposes.
   The returned reason is not for humans - it is the correction the
   LLM brain will be shown when it proposes something illegal.
3. fallback - a complete rule-based brain. Moss behaves with no model
   at all, which makes it the baseline the LLM must beat: if the
   neural brain's fallback-rate exceeds the reflexes' rate, it is
   expensive decoration.

Scene lives here too, though senses.py will produce it: interfaces
belong to their consumer. Dependency direction stays one-way
(senses -> policy -> physics); nothing imports back up.

HISTORY: the grid test once caught the snack rung proposing eat with
a full stomach - preference straying outside permission. Kept here
as a warning label: the ladder serves is_legal, never the reverse.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from moss import physics as ph

ACTIONS = ("eat", "sleep", "play", "sulk")


@dataclass(frozen=True)
class Scene:
    """What Moss can sense right now. new_commits are delivered by
    tick (which fills the bowl); policy sees the bowl, not the delivery."""

    new_commits: int = 0
    hours_quiet: float = 0.0
    is_night: bool = False


@dataclass(frozen=True)
class Decision:
    """One constrained action + free expression. Frozen: a decision,
    once made, is a fact - nobody edits history in place."""

    action: str
    thought: str = ""
    diary: str = ""
    mood: str | None = None   # None = keep current mood
    wish: str | None = None


def is_legal(action: str, state: dict[str, Any], scene: Scene) -> tuple[bool, str]:
    """The veto. Returns (verdict, reason-for-the-brain)."""
    if action not in ACTIONS:
        return False, f"unknown action {action!r}; legal actions: {ACTIONS}"
    hunger = state["drives"]["hunger"]
    energy = state["drives"]["energy"]
    bowl = state["bowl"]["commits"]

    if action == "eat":
        if bowl == 0:
            return False, "the bowl is empty - nothing to eat"
        if hunger <= ph.FULL_STOMACH:
            return False, f"not hungry enough to eat (hunger {hunger:.2f})"
        return True, ""
    if action == "sleep":
        if scene.is_night:
            return True, ""
        if energy < ph.TIRED_BELOW:
            return True, ""
        return False, "too awake to sleep before nightfall"
    if action == "play":
        if energy <= ph.MIN_PLAY_ENERGY:
            return False, f"too tired to play (energy {energy:.2f})"
        return True, ""
    return True, ""   # sulk: a protest needs no permission


# -- the fallback brain: deterministic, total, and legible ---------

# Canned voice, rotated by diary length: deterministic variety with
# zero randomness, so tests can pin it exactly.
_VOICE: dict[str, tuple[str, str]] = {
    "eat": ("Commits again. Nourishing, joyless.",
            "Ate well. The code was bitter, but food is food."),
    "sleep": ("The terminal hums me to sleep.",
              "Darkness. Soft. The fans whisper goodnight."),
    "play": ("Chased a phantom process around the filesystem.",
             "Refactored a pebble. A fine game."),
    "sulk": ("The repo is silent. Noted. Remembered.",
             "No commits. I have filed a grievance with the void."),
}
_MOODS = {"eat": "content", "sleep": "sleepy", "play": "playful", "sulk": "sulky"}
_WISHES = {"sulk": "a commit, any commit"}


def _decide(action: str, state: dict[str, Any], thought: str) -> Decision:
    lines = _VOICE[action]
    i = len(state["diary"]) % len(lines)
    return Decision(action=action, thought=thought, diary=lines[i],
                    mood=_MOODS[action], wish=_WISHES.get(action))


def fallback(state: dict[str, Any], scene: Scene) -> Decision:
    """The reflex ladder. Same state + scene -> same Decision, forever.

    Ordered by urgency. Every rung's action is legal whenever that
    rung is reached - asserted exhaustively by the grid test.
    """
    hunger = state["drives"]["hunger"]
    energy = state["drives"]["energy"]
    bowl = state["bowl"]["commits"]

    if bowl > 0 and hunger > ph.EAT_WHEN_HUNGRIER_THAN:
        return _decide("eat", state, f"hunger {hunger:.2f}, {bowl} commits waiting")
    if scene.is_night:
        return _decide("sleep", state, "night has fallen; even Moss beds down")
    if energy < ph.TIRED_BELOW:
        return _decide("sleep", state, f"energy {energy:.2f}; shutting one eye")
    if bowl > 0 and hunger > ph.FULL_STOMACH:
        return _decide("eat", state, "there is food; I am peckish")
    if energy > ph.RESTLESS_ABOVE:
        return _decide("play", state, "energy to burn and nothing to eat")
    if scene.hours_quiet >= ph.SULK_AFTER_QUIET_HOURS:
        return _decide("sulk", state, f"{scene.hours_quiet:.0f}h of silence")
    return _decide("play", state, "pottering about the working tree")