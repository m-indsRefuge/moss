"""The real entrypoint: argparse, cwd, disk. Hermetic via a barrier
.git (git walks UP the tree) and monkeypatched cwd."""
import json

import pytest

from moss.cli import main


@pytest.fixture
def pet_home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # barrier: a stray .git keeps GitSenses hermetic on any machine
    (tmp_path / ".git").write_text("gitdir: nowhere\n", encoding="utf-8")
    return tmp_path


def test_status_unhatched_is_a_friendly_hint(pet_home, capsys):
    assert main(["status"]) == 0
    assert "hatch" in capsys.readouterr().out


def test_tick_hatches_and_persists(pet_home, capsys):
    assert main(["tick"]) == 0
    out = capsys.readouterr().out
    assert "hatches" in out
    assert "Moss (" in out                       # the status line
    brain = pet_home / "moss.state.json"
    assert brain.exists()
    assert json.loads(brain.read_text(encoding="utf-8"))["name"] == "Moss"


def test_status_after_tick_renders_the_pet(pet_home, capsys):
    main(["tick"])
    capsys.readouterr()
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "hunger" in out and "bowl" in out
    assert "last diary" in out


def test_second_tick_appends_to_the_diary(pet_home):
    main(["tick"])
    main(["tick"])
    brain = json.loads((pet_home / "moss.state.json").read_text(encoding="utf-8"))
    assert len(brain["diary"]) == 2


def test_corrupt_brain_is_loud_and_untouched(pet_home, capsys):
    brain = pet_home / "moss.state.json"
    brain.write_text("not json {{{", encoding="utf-8")
    assert main(["status"]) == 1
    assert "not valid JSON" in capsys.readouterr().err
    assert brain.read_text(encoding="utf-8") == "not json {{{"   # never reset


# -- the pure renderers ---------------------------------------------

def test_format_status_shows_drives_and_bowl():
    from datetime import datetime, timezone
    from moss.cli import format_status
    from moss.state import new_state
    s = new_state("Moss", datetime(2025, 1, 1, tzinfo=timezone.utc))
    s["bowl"]["commits"] = 4
    text = format_status(s)
    assert "Moss (content)" in text and "hunger 0.35" in text and "bowl 4" in text


def test_format_tick_marks_reflex_fallback():
    from datetime import datetime, timezone
    from moss.brain import BrainReply
    from moss.cli import format_tick
    from moss.policy import Scene, fallback
    from moss.state import new_state
    from moss.tick import TickResult
    s = new_state("Moss", datetime(2025, 1, 1, tzinfo=timezone.utc))
    r = TickResult(state=s, scene=Scene(),
                   reply=BrainReply(fallback(s, Scene()), 2, True),
                   filled=0, ate=0)
    assert "[reflex fallback]" in format_tick(r)