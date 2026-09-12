"""Architecture fitness function: time is injected, never queried.

Moss is simulatable for exactly one reason: no module touches wall time.
This test enforces that rule forever.
"""
from pathlib import Path

SRC = Path(__file__).parent.parent / "src" / "moss"
BANNED = ("datetime.now(", "datetime.utcnow(", "time.time(", "time.monotonic(")


def test_wall_time_is_only_accessed_via_clock():
    offenders = []
    for f in sorted(SRC.glob("*.py")):
        if f.name == "clock.py":
            continue
        text = f.read_text(encoding="utf-8")
        offenders += [f"{f.name}: {b}" for b in BANNED if b in text]
    assert not offenders, f"Direct time access outside clock.py: {offenders}"