"""Architecture fitness functions.

1. Time is injected, never queried (clock.py's monopoly).
2. Every I/O mechanism has exactly ONE owner module. A renderer, a
   refactor, or a well-meaning AI contributor cannot scatter git
   calls, HTTP, or disk writes across the codebase without the gate
   going red. The one-owner map IS the architecture.
"""
from pathlib import Path

SRC = Path(__file__).parent.parent / "src" / "moss"
QML = SRC / "qml"

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


def test_qml_does_not_own_lifecycle_timers():
    allowed_visual_timer = (
        'Timer { id: settle; interval: 4200; '
        'onTriggered: creature.state = "idle" }'
    )
    offenders = []

    for f in sorted(QML.glob("*.qml")):
        text = f.read_text(encoding="utf-8")
        timers = [
            line.strip()
            for line in text.splitlines()
            if "Timer {" in line
        ]

        for timer in timers:
            if f.name == "Creature.qml" and timer == allowed_visual_timer:
                continue
            offenders.append(f"{f.name}: {timer}")

    assert not offenders, f"Unapproved QML Timer found: {offenders}"
