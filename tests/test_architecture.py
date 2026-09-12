"""Architecture fitness functions.

1. Time is injected, never queried (clock.py's monopoly).
2. Every I/O mechanism has exactly ONE owner module. A renderer, a
   refactor, or a well-meaning AI contributor cannot scatter git
   calls, HTTP, or disk writes across the codebase without the gate
   going red. The one-owner map IS the architecture.

These are substring tripwires aimed at ACCIDENTS, not adversaries:
they catch a well-meaning `import subprocess` drifting into brain.py,
not deliberate evasion. Mechanism strings are chosen to match real
calls - "json.dump(" is paren-qualified so llm.py's json.dumps(
payload serialization (string out, no file handle) stays legal while
state.py's file-writing json.dump( remains the monopoly.

HISTORY: this test once failed on its own author - "json.dump"
substring-matched llm.py's innocent json.dumps. Kept as a warning:
tripwires need testing too, and the first thing they catch is often
the person who set them.
"""
from pathlib import Path

SRC = Path(__file__).parent.parent / "src" / "moss"

TIME_BANNED = ("datetime.now(", "datetime.utcnow(", "time.time(", "time.monotonic(")

# mechanism -> the only module allowed to mention it
MONOPOLIES = {
    "subprocess": ("senses.py",),
    "urllib": ("llm.py",),
    "os.replace": ("state.py",),
    "os.fsync": ("state.py",),
    "json.dump(": ("state.py",),
    "argparse": ("cli.py",),
    "print(": ("cli.py",),
    "textual": ("tui.py",),
}


def test_wall_time_is_only_accessed_via_clock():
    offenders = []
    for f in sorted(SRC.glob("*.py")):
        if f.name == "clock.py":
            continue
        text = f.read_text(encoding="utf-8")
        offenders += [f"{f.name}: {b}" for b in TIME_BANNED if b in text]
    assert not offenders, f"Direct time access outside clock.py: {offenders}"


def test_each_io_mechanism_has_exactly_one_owner():
    offenders = []
    for f in sorted(SRC.glob("*.py")):
        text = f.read_text(encoding="utf-8")
        for mechanism, owners in MONOPOLIES.items():
            if f.name in owners:
                continue
            if mechanism in text:
                offenders.append(f"{f.name} uses {mechanism!r} (owned by {owners})")
    assert not offenders, f"Monopoly violations: {offenders}"