# HANDOFF - collaborating on Moss

This repo has a tested, frozen agent core and an open invitation to
build UI on top of it. Read this before writing anything.

## The rules (learned the hard way)

1. ONE writer at a time. AI collaborators review or build in their
   lane; they never silently rewrite files outside it.
2. The gate is the referee. Run `pytest -q` before every commit.
   A red gate means stop, not "fix forward."
3. Receipts after every change: the pytest line + `git log --oneline -1`.
4. The drift audit, runnable any time:

       git diff --name-only core-v1..HEAD -- src/moss

   Allowed to differ: `tui.py`, `cli.py` (only to add a `moss tui`
   subcommand), `__init__.py` (only to bump version). Anything else
   is core drift - revert and discuss.

## Frozen vs. open

- FROZEN: `clock.py`, `state.py`, `physics.py`, `policy.py`,
  `brain.py`, `senses.py`, `tick.py`, `llm.py` - all contract-tested
  (see `tests/test_contracts.py`, which is the source of truth for
  every data shape) and tripwired (see `tests/test_architecture.py`:
  subprocess lives only in senses, urllib only in llm, disk writes
  only in state, printing only in cli).
- OPEN: `tui.py` (new), the `[tui]` extra in `pyproject.toml`
  (`textual>=0.60`), a `moss tui` subcommand in `cli.py`.

## What a UI needs to know

- Compose, never reimplement: drive the pet through
  `tick(state, clock, senses, brain)` with injected
  `RealClock`/`SimClock`, `GitSenses`/`FixtureSenses`, and a brain.
  There is no other correct way to change state.
- Headless example (this is the whole integration):

      from moss.state import load, new_state
      from moss.clock import RealClock
      from moss.senses import GitSenses
      from moss.brain import ReflexBrain
      from moss.tick import tick

      s = load(path) or new_state("Moss", RealClock().now())
      result = tick(s, RealClock(), GitSenses(repo_dir), ReflexBrain())
      # result.state -> save via moss.state.save; render anything

- Data shapes: `tests/test_contracts.py` pins every field. The brain
  file schema (drives, bowl, mood, diary, stats, wish) is versioned
  and load()-validated - never hand-write state dicts.
- Mood is FREE EXPRESSION: `policy.KNOWN_MOODS` is what the reflex
  brain emits and the minimum face set to design; the LLM may write
  anything up to 80 chars. Unknown mood -> fallback face. Mood is
  never an enum.
- Simulation for demos/tests: `SimClock` + `FixtureSenses(steps)` +
  `ReflexBrain` over an in-memory dict - zero disk, zero network,
  zero model. N scenario steps = N ticks. 100 days run in under a
  second. Never write simulated state to a real brain file.
- LLM ticks are slow and may fail: a cold model load takes minutes
  (run them in a worker thread; the CLI prints a stderr hint), and
  any failure degrades to reflexes - look for `used_fallback` on
  `BrainReply` and surface it honestly in the UI.
- Known live behavior: the pet can choose to sulk instead of eat
  with food in the bowl. That is personality, not a bug; the veto
  only blocks ILLEGAL actions. Report `used_fallback` rate, never
  paper over it.