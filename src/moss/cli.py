"""The only place Moss touches reality: the console and the brain file.

  moss tick    - live one tick (hatches on first run)
  moss status  - look, don't touch

The brain file lives in the CURRENT DIRECTORY: you cd into a repo,
run `moss tick`, and that repo gets its own pet. (The scaffold's
.gitignore already excludes moss.state.json - a brain is runtime
data, not source.) M0 default brain is ReflexBrain: the creature is
complete with no model at all. The LLM transport and --brain llm
arrive in the next block and plug into the same tick.

Corrupt brains are LOUD here too: exit code 1, file untouched. The
promise made in state.py ends at the keyboard, not before it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from moss.brain import ReflexBrain
from moss.clock import RealClock
from moss.senses import GitSenses
from moss.state import CorruptStateError, load, new_state, save
from moss.tick import TickResult, tick

STATE_FILENAME = "moss.state.json"


# -- rendering: pure, tested, ASCII-humble (console codepages vary) --

def format_status(s: dict[str, Any]) -> str:
    d = s["drives"]
    return (f"{s['name']} ({s['mood']}) - hunger {d['hunger']:.2f}, "
            f"energy {d['energy']:.2f}, bowl {s['bowl']['commits']}")


_ACTION_DETAIL = {
    "eat": lambda r: f"ate {r.ate} commit(s)",
    "sleep": lambda r: "rested",
    "play": lambda r: "played",
    "sulk": lambda r: "protested the silence",
}


def format_tick(r: TickResult) -> str:
    verb = r.reply.decision.action.capitalize()
    detail = _ACTION_DETAIL[r.reply.decision.action](r)
    mark = "  [reflex fallback]" if r.reply.used_fallback else ""
    diary = f' - "{r.reply.decision.diary}"' if r.reply.decision.diary else ""
    return f"{verb}: {detail}{mark}{diary}"


# -- commands ------------------------------------------------------

def cmd_tick() -> int:
    cwd = Path.cwd()
    path = cwd / STATE_FILENAME
    try:
        existing = load(path)
    except CorruptStateError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if existing is None:
        existing = new_state("Moss", RealClock().now())
        print(f"{existing['name']} hatches. Commits are food; the repo is home.")
    result = tick(existing, RealClock(), GitSenses(cwd), ReflexBrain())
    save(path, result.state)
    print(format_status(result.state))
    print(format_tick(result))
    return 0


def cmd_status() -> int:
    path = Path.cwd() / STATE_FILENAME
    try:
        s = load(path)
    except CorruptStateError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if s is None:
        print("No Moss lives here yet. Run 'moss tick' to hatch one.")
        return 0
    print(format_status(s))
    if s["diary"]:
        print(f'last diary: "{s["diary"][-1]}"')
    if s["wish"]:
        print(f"wish: {s['wish']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="moss", description="a terminal pet that feeds on your git activity")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("tick", help="live one tick (hatches on first run)")
    sub.add_parser("status", help="look, don't touch")
    args = p.parse_args(argv)
    return cmd_tick() if args.command == "tick" else cmd_status()


if __name__ == "__main__":
    sys.exit(main())