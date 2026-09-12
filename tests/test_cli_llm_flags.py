"""The M1.5 finishing touches: --timeout plumbs through, and the
cold-load hint reaches stderr so silence is never mistaken for a hang."""
import json


from moss.cli import main



def _pet_home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").write_text("gitdir: nowhere\n", encoding="utf-8")
    return tmp_path


def test_timeout_flag_plumbs_through_and_still_degrades(tmp_path, monkeypatch, capsys):
    _pet_home(tmp_path, monkeypatch)
    rc = main(["tick", "--brain", "llm", "--model", "ghost:latest",
               "--timeout", "0.5", "--ollama-url", "http://127.0.0.1:1"])
    assert rc == 0
    assert "[reflex fallback]" in capsys.readouterr().out


def test_llm_brain_prints_cold_load_hint_to_stderr(tmp_path, monkeypatch, capsys):
    _pet_home(tmp_path, monkeypatch)
    main(["tick", "--brain", "llm", "--model", "qwen3:14b",
          "--ollama-url", "http://127.0.0.1:1"])
    captured = capsys.readouterr()
    assert "Ollama" in captured.err and "minutes" in captured.err
    assert "[reflex fallback]" in captured.out      # degradation still held
    brain = json.loads((tmp_path / "moss.state.json").read_text(encoding="utf-8"))
    assert brain["name"] == "Moss"