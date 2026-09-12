"""End to end through the real CLI: --brain llm with an unreachable
server still ticks, degrades to reflexes, and says so out loud."""
import json


from moss.cli import main



def test_llm_brain_with_dead_transport_degrades_to_reflexes(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    # barrier: git walks UP the tree; keep GitSenses hermetic anywhere
    (tmp_path / ".git").write_text("gitdir: nowhere\n", encoding="utf-8")
    rc = main(["tick", "--brain", "llm", "--model", "ghost:latest",
               "--ollama-url", "http://127.0.0.1:1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "hatches" in out
    assert "[reflex fallback]" in out
    brain = json.loads((tmp_path / "moss.state.json").read_text(encoding="utf-8"))
    assert brain["name"] == "Moss"