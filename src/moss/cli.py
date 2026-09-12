"""The only place Moss touches reality: the console and the brain file.

  moss tick    - live one tick (hatches on first run)
  moss status  - look, don't touch

Brain selection (per tick, not persisted):
  --brain reflex            the deterministic ladder (default)
  --brain llm --model M     a real model over Ollama (--timeout for
                            slow machines: a cold 14B load can take
                            minutes; the hint on stderr says so)

The brain file lives in the CURRENT DIRECTORY: cd into a repo, run
`moss tick`, and that repo gets its own pet. With --brain llm and no
server running, the tick still succeeds via reflexes - and the
[reflex fallback] marker says so out loud. The pet cannot die
because its brain is unreachable; it just gets simpler.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from moss.brain import LLMBrain, ReflexBrain
from moss.clock import RealClock
from moss.llm import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_S,
    OllamaLLM,
)
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

def cmd_tick(args: argparse.Namespace) -> int:
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

    if args.brain == "llm":
        # stderr on purpose: stdout stays parseable; the hint exists
        # so a slow first load is never mistaken for a hang again
        print(f"asking {args.model} via Ollama - first call may take "
              "minutes to load the model", file=sys.stderr)
        transport = OllamaLLM(model=args.model, base_url=args.ollama_url,
                              temperature=args.temperature,
                              timeout_s=args.timeout)
        brain = LLMBrain(transport)
    else:
        brain = ReflexBrain()

    result = tick(existing, RealClock(), GitSenses(cwd), brain)
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

    p_tick = sub.add_parser("tick", help="live one tick (hatches on first run)")
    p_tick.add_argument("--brain", choices=["reflex", "llm"], default="reflex")
    p_tick.add_argument("--model", default=DEFAULT_MODEL)
    p_tick.add_argument("--ollama-url", default=DEFAULT_BASE_URL)
    p_tick.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    p_tick.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)

    sub.add_parser("status", help="look, don't touch")

    p_home = sub.add_parser("home", help="open Moss's graphical habitat")
    p_home.add_argument("--brain", choices=["reflex", "llm"], default="reflex")
    p_home.add_argument("--model", default=DEFAULT_MODEL)
    p_home.add_argument("--ollama-url", default=DEFAULT_BASE_URL)
    p_home.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    p_home.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)

    args = p.parse_args(argv)
    if args.command == "tick":
        return cmd_tick(args)
    if args.command == "home":
        # Optional GUI dependency: headless commands never import Qt.
        try:
            from moss.gui import run_home
        except ModuleNotFoundError as e:
            if e.name and e.name.startswith("PySide6"):
                print('moss home requires PySide6; install moss with the [gui] extra.',
                      file=sys.stderr)
                return 1
            raise
        from moss.runtime import configured_runtime
        return run_home(configured_runtime(
            Path.cwd(), brain=args.brain, model=args.model,
            ollama_url=args.ollama_url, temperature=args.temperature,
            timeout=args.timeout))
    return cmd_status()


if __name__ == "__main__":
    sys.exit(main())
