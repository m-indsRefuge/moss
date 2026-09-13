from datetime import datetime, timezone

from moss.brain import (
    MAX_ATTEMPTS,
    LLMBrain,
    ReflexBrain,
    StubLLM,
    build_prompt,
    parse_decision,
)
from moss.policy import Scene, fallback
from moss.state import new_state, validate

T0 = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
DAY = Scene(is_night=False, hours_quiet=5.0)


def make_state(hunger=0.9, energy=0.45, bowl=3, diary=()):
    s = new_state("Moss", T0)
    s["drives"] = {"hunger": hunger, "energy": energy}
    s["bowl"]["commits"] = bowl
    s["diary"] = list(diary)
    return s


PERFECT = """THOUGHT: The bowl is full and my stomach is a void.
ACTION: eat
MOOD: smug
DIARY: Three commits, gone in one bite.
WISH: moar commits"""


# -- parsing: syntax only -----------------------------------------

def test_parse_perfect_reply():
    d = parse_decision(PERFECT)
    assert d is not None
    assert d.action == "eat"
    assert d.mood == "smug"
    assert d.wish == "moar commits"
    assert "Three commits" in d.diary


def test_parse_tolerates_messy_formatting():
    messy = """
Alright, here is what I decide!

thought: my tummy rumbles
ACTION - `eat`
mood: "smug"
DIARY:   Ate well. "Burp."
WISH: none

Hope that helps!
"""
    d = parse_decision(messy)
    assert d is not None
    assert d.action == "eat"
    assert d.mood == "smug"
    assert d.diary == 'Ate well. "Burp."'   # inner quotes survive
    assert d.wish is None                    # 'none' means none


def test_parse_missing_action_returns_none():
    assert parse_decision("I love cheese. Cheese is all.") is None
    assert parse_decision("THOUGHT: hmm\nDIARY: quiet day") is None


def test_parse_empty_optionals_become_none():
    d = parse_decision("ACTION: play\nMOOD:\nDIARY:   \nWISH: n/a")
    assert d is not None and d.action == "play"
    assert d.mood is None and d.diary == "" and d.wish is None


def test_parse_truncates_oversized_expression():
    d = parse_decision(f"ACTION: eat\nMOOD: {'x' * 300}\nDIARY: {'y' * 5000}")
    assert d is not None
    assert len(d.mood) <= 80 and len(d.diary) <= 200


def test_expression_can_never_fail_state_validation():
    """The model's wildest mood must not be able to crash save()."""
    d = parse_decision(f"ACTION: eat\nMOOD: {'odd' * 100}")
    s = make_state()
    s["mood"] = d.mood
    validate(s)   # no exception


# -- the prompt ----------------------------------------------------

def test_prompt_contains_scene_and_contract():
    p = build_prompt(make_state(hunger=0.9, energy=0.45, bowl=3), DAY)
    assert "Moss" in p
    assert "hunger 0.90" in p and "starving" in p
    assert "energy 0.45" in p and "tired" in p
    assert "bowl holds 3" in p
    assert "daytime" in p and "quiet for 5h" in p
    for label in ("THOUGHT:", "ACTION:", "MOOD:", "DIARY:", "WISH:"):
        assert label in p
    for action in ("eat", "sleep", "play", "sulk"):
        assert action in p
    assert "Example reply" in p   # tiny models copy patterns, not specs


def test_prompt_carries_recent_memory():
    s = make_state(diary=["d1", "d2", "d3", "d4"])
    p = build_prompt(s, DAY)
    assert "- d2" in p and "- d3" in p and "- d4" in p
    assert "d1" not in p          # the ring buffer keeps the last 3


def test_prompt_is_deterministic():
    s = make_state()
    assert build_prompt(s, DAY) == build_prompt(s, DAY)


def test_prompt_contains_compact_diary_voice_guidance():
    p = build_prompt(make_state(diary=["The repository is being suspiciously sensible."]), DAY)
    assert "Diary voice:" in p
    assert "8–24 words" in p
    assert "dry and observational first" in p
    assert "Vary sentence structure, verbs, and metaphors" in p
    assert "do not make every diary entry about food or taste" in p
    assert "one concrete observation" in p
    assert "When work categories are mixed" in p
    assert "Avoid repeating wording, jokes" in p
    assert "or wishes" in p
    assert "never invent dates, tools, causes" in p
    assert "The repository is being suspiciously sensible." in p


# -- the decide loop: nudge, veto, degrade ------------------------

def test_brain_happy_path():
    stub = StubLLM([PERFECT])
    reply = LLMBrain(stub).decide(make_state(), DAY)
    assert reply.decision.action == "eat"
    assert reply.decision.mood == "smug"
    assert reply.attempts == 1 and not reply.used_fallback


def test_veto_reason_reaches_the_model():
    """The money test: an illegal proposal comes back with the reason."""
    sleepy = "THOUGHT: cozy\nACTION: sleep\nMOOD: sleepy\nDIARY: nap time\nWISH: none"
    stub = StubLLM([sleepy, PERFECT])
    reply = LLMBrain(stub).decide(make_state(energy=0.9), DAY)
    assert reply.decision.action == "eat"
    assert reply.attempts == 2 and not reply.used_fallback
    assert "illegal right now" in stub.prompts[1]
    assert "too awake to sleep before nightfall" in stub.prompts[1]


def test_format_failure_nudges_then_falls_back():
    stub = StubLLM(["I love cheese.", "still no"])
    reply = LLMBrain(stub).decide(make_state(), DAY)
    assert reply.used_fallback
    assert reply.attempts == MAX_ATTEMPTS
    assert reply.decision == fallback(make_state(), DAY)
    assert "broke the format" in stub.prompts[1]


def test_transport_crash_degrades_to_reflexes():
    class BoomLLM:
        def complete(self, prompt):
            raise RuntimeError("ollama is down")

    reply = LLMBrain(BoomLLM()).decide(make_state(), DAY)
    assert reply.used_fallback                    # no exception escaped
    assert reply.decision == fallback(make_state(), DAY)


def test_stub_exhaustion_counts_as_transport_failure():
    reply = LLMBrain(StubLLM([])).decide(make_state(), DAY)
    assert reply.used_fallback


def test_stub_replies_in_order_and_records_prompts():
    stub = StubLLM(["first", "second"])
    assert stub.complete("p1") == "first"
    assert stub.complete("p2") == "second"
    assert stub.prompts == ["p1", "p2"]


# -- the baseline ---------------------------------------------------

def test_reflex_brain_is_the_baseline():
    s = make_state()
    reply = ReflexBrain().decide(s, DAY)
    assert reply.decision == fallback(s, DAY)
    assert reply.attempts == 0 and not reply.used_fallback
