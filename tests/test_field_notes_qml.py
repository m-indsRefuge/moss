from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "src" / "moss" / "qml" / "Home.qml"


def test_field_notes_has_explicit_journal_hierarchy_and_stays_presentation_only():
    source = HOME.read_text(encoding="utf-8")
    notes_start = source.index('id: notes; objectName: "notesRegion"')
    notes_end = source.index("// Persistent footer:")
    notes = source[notes_start:notes_end]

    for marker in (
        'objectName: "journalPage"',
        'objectName: "journalEntry"',
        'objectName: "journalAnnotation"',
        'objectName: "journalArchiveMeta"',
    ):
        assert marker in notes

    for preserved in (
        'objectName: "latestDiary"',
        'objectName: "thoughtLabel"',
        'objectName: "historyButton"',
        'objectName: "diaryHistory"',
        'objectName: "lifetimeSummary"',
        'objectName: "mealSummary"',
    ):
        assert preserved in notes

    forbidden = (
        "requestTick(",
        "requestClose(",
        "open()",
        "moss.state.json",
        "subprocess",
        "ollama",
        "qwen",
    )
    lowered = notes.lower()
    assert all(token.lower() not in lowered for token in forbidden)
