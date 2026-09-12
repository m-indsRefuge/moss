"""The neural personality - and the protocol engineering around it.

The brain NEVER touches state, never sees the clock, and cannot crash
the pet. Its entire world: a flat prompt in, a Decision out.

Design for a small model:
- ONE flat prompt, not multi-turn chat. Tiny models copy patterns;
  they do not hold conversations. One worked example, fixed forever.
- State is translated into the model language ("starving", not 0.87).
- The model is treated as an UNRELIABLE EXTERNAL SERVICE: timeouts,
  garbage, and illegal proposals are all just "an unusable reply" and
  cost one retry. After MAX_ATTEMPTS, the reflexes take over. The
  pet must never die because its brain hiccuped.
- Expression is sanitized at the boundary (length caps): the mood and
  diary channels must never be able to fail state validation.

Every reply carries metadata (attempts, used_fallback) so tick can
tally the fallback-rate: how often the neural brain held the leash.

HISTORY: the empty-optionals test caught _field using \\s* after the
label colon - and \\s spans newlines, so an empty MOOD: line swallowed
the next label as its value. Field values end at their own line;
whitespace after a label is [ \\t]*, never \\s*.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from moss.policy import Decision, Scene, fallback, is_legal

MAX_ATTEMPTS = 2   # cost ceiling: a tick spends at most 2 completions


class LLM(Protocol):
    """The one method a transport must provide (Ollama now, others later)."""

    def complete(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class BrainReply:
    """A Decision plus the telemetry of how it was reached."""

    decision: Decision
    attempts: int
    used_fallback: bool


# -- the prompt: state, translated --------------------------------

TEMPLATE = """You are {name}, a small creature living inside a git repository. Commits are your food.

Right now: {hunger_word} (hunger {hunger:.2f}), {energy_word} (energy {energy:.2f}).
Your bowl holds {bowl} uneaten commit(s). It is {day_or_night}. The repo has been quiet for {quiet:.0f}h.
Your mood: {mood}. Life so far: {meals} meal(s) eaten, {sulks} sulk(s).
Recent diary:
{diary_block}

Choose ONE action:
- eat   - empty the bowl (illegal if the bowl is empty or you are full)
- sleep - rest (illegal in daytime unless you are exhausted)
- play  - amuse yourself (illegal when exhausted)
- sulk  - protest the silence (always allowed)

Reply with EXACTLY five lines:
THOUGHT: <one sentence of inner monologue>
ACTION: <one of: eat, sleep, play, sulk>
MOOD: <one or two words describing your mood>
DIARY: <one first-person sentence about what you are doing>
WISH: <one short wish, or write none>

Example reply:
THOUGHT: My stomach growls and three commits wait in the bowl.
ACTION: eat
MOOD: content
DIARY: Ate the morning commits. They tasted of coffee and ambition.
WISH: a quiet afternoon

Your reply:"""


def _hunger_word(v: float) -> str:
    if v >= 0.8: return "starving"
    if v >= 0.6: return "very hungry"
    if v >= 0.3: return "peckish"
    return "full"


def _energy_word(v: float) -> str:
    if v >= 0.8: return "bursting with energy"
    if v >= 0.5: return "rested"
    if v >= 0.3: return "tired"
    return "exhausted"


def build_prompt(state: dict[str, Any], scene: Scene) -> str:
    """Render the whole world into one flat prompt. Deterministic:
    same state + scene, same bytes - no hidden clock, no randomness."""
    d, st = state["drives"], state["stats"]
    diary = state["diary"][-3:]   # memory: the last three entries
    diary_block = "\n".join(f"- {line}" for line in diary) if diary else "- (no entries yet)"
    return TEMPLATE.format(
        name=state["name"],
        hunger=d["hunger"], energy=d["energy"],
        hunger_word=_hunger_word(d["hunger"]), energy_word=_energy_word(d["energy"]),
        bowl=state["bowl"]["commits"],
        day_or_night="night" if scene.is_night else "daytime",
        quiet=scene.hours_quiet,
        mood=state["mood"],
        meals=st["commits_eaten"], sulks=st["sulks"],
        diary_block=diary_block,
    )


# -- the parser: syntactic only; semantics live in is_legal -------

# Caps mirror/never-exceed state.validate() limits: an expression
# channel that could fail validation would be a crash the model
# could aim at the harness. It does not get that power.
_CAPS = {"thought": 200, "mood": 80, "diary": 200, "wish": 140}
_NONE_WORDS = {"", "none", "nothing", "-", "n/a", "null"}


def _field(text: str, label: str) -> str | None:
    """Grab one label's value. Values END at their line: whitespace
    after the label is [ \\t]* - \\s* would match the newline itself
    and let the capture spill into the next field's label."""
    m = re.search(rf"^[ \t]*{label}[ \t]*[:\-][ \t]*(.*)$", text,
                  re.IGNORECASE | re.MULTILINE)
    return m.group(1) if m else None


def _clean(value: str | None, cap: int) -> str | None:
    """Tolerant cleanup: whitespace, wrapping quotes, 'none' words, cap."""
    if value is None:
        return None
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1].strip()
    if v.lower() in _NONE_WORDS:
        return None
    return v[:cap]


def parse_decision(text: str) -> Decision | None:
    """Extract a Decision from free text. None = no ACTION line at all.

    Tolerates: any label case, '-' as separator, surrounding prose,
    backticked/quoted values. UNKNOWN actions parse fine on purpose -
    syntax is this module's job; legality is is_legal's.
    """
    raw_action = _clean(_field(text, "ACTION"), 20)
    if raw_action is None:
        return None
    action = raw_action.lower().strip("`.,!;: ")
    return Decision(
        action=action,
        thought=_clean(_field(text, "THOUGHT"), _CAPS["thought"]) or "",
        diary=_clean(_field(text, "DIARY"), _CAPS["diary"]) or "",
        mood=_clean(_field(text, "MOOD"), _CAPS["mood"]),
        wish=_clean(_field(text, "WISH"), _CAPS["wish"]),
    )


# -- corrections: the veto reason, fed back to the model ----------

FORMAT_NUDGE = (
    "Your previous reply broke the format. Reply with EXACTLY five lines "
    "beginning THOUGHT:, ACTION:, MOOD:, DIARY:, WISH:. "
    "ACTION must be one of: eat, sleep, play, sulk."
)

ILLEGAL_NUDGE = (
    'Your previous reply proposed "{action}", which is illegal right now: {why}. '
    "Consider the situation and reply again in the same format with a LEGAL action."
)


# -- the brains ----------------------------------------------------

class LLMBrain:
    """The neural personality. Proposes; the harness disposes."""

    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def decide(self, state: dict[str, Any], scene: Scene) -> BrainReply:
        prompt = build_prompt(state, scene)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                raw = self.llm.complete(prompt)
            except Exception:   # transport died: treat as an unusable reply
                raw = ""
            decision = parse_decision(raw)
            if decision is not None:
                ok, why = is_legal(decision.action, state, scene)
                if ok:
                    return BrainReply(decision, attempt, used_fallback=False)
                nudge = ILLEGAL_NUDGE.format(action=decision.action, why=why)
            else:
                nudge = FORMAT_NUDGE
            shown = raw if raw.strip() else "(the model returned nothing usable)"
            prompt += f"\n\n=== YOUR PREVIOUS REPLY ===\n{shown}\n=== CORRECTION ===\n{nudge}\n=== REPLY AGAIN ==="
        return BrainReply(fallback(state, scene), MAX_ATTEMPTS, used_fallback=True)


class ReflexBrain:
    """Moss with no model at all: pure reflexes, attempts=0.

    Exists so the same harness can A/B the brains: does the LLM
    actually behave better than the ladder?
    """

    def decide(self, state: dict[str, Any], scene: Scene) -> BrainReply:
        return BrainReply(fallback(state, scene), 0, used_fallback=False)


class StubLLM:
    """Scripted replies, popped in order. The offline test double.

    Also records every prompt it receives - tests assert on what the
    brain SAID to the model, not just what came back. Script exactly
    as many replies as the brain should request: exhaustion surfaces
    as a transport failure, which decide() degrades to reflexes.
    """

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._replies:
            raise RuntimeError("StubLLM out of scripted replies")
        return self._replies.pop(0)