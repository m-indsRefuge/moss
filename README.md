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