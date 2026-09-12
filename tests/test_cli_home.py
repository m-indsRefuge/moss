"""GUI launch stays optional and leaves existing CLI defaults intact."""
import builtins
import sys
from types import ModuleType

from moss.brain import LLMBrain, ReflexBrain
from moss.cli import main


def test_home_flags_construct_runtime_without_running_tick(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    gui = ModuleType("moss.gui")
    gui.run_home = lambda runtime: calls.append(runtime) or 17
    monkeypatch.setitem(sys.modules, "moss.gui", gui)
    assert main(["home"]) == 17
    assert isinstance(calls[-1].brain, ReflexBrain)
    assert main(["home", "--brain", "llm", "--model", "qwen-test",
                 "--ollama-url", "http://127.0.0.1:1", "--timeout", "3",
                 "--temperature", "0.2"]) == 17
    runtime = calls[-1]
    assert runtime.repo == tmp_path and not runtime.state_path.exists()
    assert isinstance(runtime.brain, LLMBrain)
    assert runtime.brain.llm.model == "qwen-test"
    assert runtime.brain.llm.timeout_s == 3 and runtime.brain.llm.temperature == 0.2
    assert runtime.brain.llm.base_url == "http://127.0.0.1:1"


def test_home_missing_qt_is_friendly_but_status_never_imports_it(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    original = builtins.__import__
    def without_gui(name, *args, **kwargs):
        if name == "moss.gui":
            raise ModuleNotFoundError("No module named PySide6", name="PySide6")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", without_gui)
    assert main(["status"]) == 0
    assert main(["home"]) == 1
    assert "[gui] extra" in capsys.readouterr().err
