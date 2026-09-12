# Moss

A terminal pet that lives in your git repo. Commits are food. Neglect the
repo and Moss starves and sulks; ship a feature branch and it feasts.

Architecture: the harness is Moss metabolism (deterministic Python -
hunger, energy, time, git facts); a tiny local LLM is its personality
(one constrained action + one diary line per tick).

Roadmap:
- M0 - metabolism: state, clock injection, physics, fallback policy
- M1 - the brain: prompt, parse, retry; Ollama adapter
- M2 - move in: scheduled ticks, MOSS_DIARY.md
- M3 - endurance: moss simulate --days 100

## Dev setup

    py -3 -m venv .venv
    .\.venv\Scripts\pip install -e ".[dev]"
    .\.venv\Scripts\pytest

## Living window (GUI-01)

Install the optional GUI dependency in the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,gui]"
.\.venv\Scripts\moss.exe home
# Opt in to the existing local Ollama brain:
.\.venv\Scripts\moss.exe home --brain llm --model qwen2.5:0.5b --timeout 120
```

Launch from the directory containing your pet. Like `moss tick`, `home` uses
`moss.state.json` in the current directory, even inside a repo subdirectory.
Opening loads the existing pet, or saves a new hatchling only if absent.
Malformed state produces an error and is never replaced with a hatchling.
`moss tick` and `moss status` retain their existing behavior and need no Qt.

Press **Live a tick** to sense Git, consult the selected brain, apply the core's
final policy decision, and persist it. There is no automatic tick or Git poll.
The character plays the saved action, then settles to idle with its current
mood. Animation timers do not change Moss. Brain/action telemetry describes
this visit; it is not added to the persistent schema.

`runtime.py` owns the load/hatch/tick/save transaction and returns frozen
snapshots. `gui.py` runs each transaction in a QThread and publishes read-only
Qt properties only after success. The runtime lock covers the entire
transaction; the bridge rejects clicks while busy. Closing waits visibly for
active work to finish, including slow model calls, without interrupting saves.
There is no unsafe thread termination or cancellation within a tick.

Limits: serialization covers one runtime instance. **Do not run a second GUI
or a state-reading/writing CLI command against that pet concurrently.** There
is no cross-process lock; even core `load()` may clean a temporary save file.
Git sensing is shown as not yet sensed, history read, or unavailable/empty.
The existing sensor conflates an empty history with Git failure, so a healthy
empty-repo indicator remains a follow-up. The frozen sensor/core is unchanged.

Validation: run `python -m pytest -q` in the project environment. Qt tests use
an offscreen window and skip when the GUI extra is absent. Install `[dev,gui]`
to run every GUI gate. Live Qwen and human visual acceptance are separate checks.
