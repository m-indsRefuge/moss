from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAILURE_MAP = ROOT / "FAILURE_MAP.md"


def test_failure_map_covers_autonomous_lifecycle_boundaries():
    text = FAILURE_MAP.read_text(encoding="utf-8")

    for marker in (
        "Autonomous timer inactive",
        "Timer fires while worker is active",
        "Duplicate or overlapping tick",
        "Close during an in-flight tick",
        "Model latency exceeds cadence",
        "Reflex fallback versus hard failure",
        "Save failure during autonomous tick",
        "Manual Check in invalidates timer",
        "Suspend or resume without catch-up",
        "Multiple Moss processes",
    ):
        assert marker in text

    required_fields = (
        "**Observable symptom:**",
        "**Likely causes:**",
        "**First diagnostics:**",
        "**Propagation risk:**",
        "**Safe recovery:**",
        "**Do not:**",
        "**Related tests:**",
    )

    # Ten lifecycle boundaries, each documented with the complete failure schema.
    for field in required_fields:
        assert text.count(field) >= 10
