# HANDOFF - collaborating on Moss

This handoff describes the current accepted Moss architecture on `main` and
the next bounded milestone. Read it before changing production code.

## Current baseline

The accepted remote baseline immediately before this handoff refresh was:

- `25df2509121d3b2f59becc5a9b768c824ed18855` — `Merge MOSS-LIFECYCLE-01`

The autonomous lifecycle milestone is integrated. Earlier accepted visual
milestones on this line include:

- `MOSS-UI-FOOD-01` — commit bowl and food-token presentation.
- `MOSS-DESKTOP-01B + 01C` — final macro desktop polish.
- `MOSS-UI-NOTES-01` — Field Notes journal hierarchy.
- `MOSS-UI-VITALS-01` — illustrated botanical Hunger and Energy meters.

Do not reimplement these milestones as new work.

## Core authority

Moss remains a deterministic Python organism with an optional local-LLM
personality layer.

The authoritative life transaction is still:

`MossRuntime.live_tick() -> tick(...)`

One completed tick:

1. applies elapsed-time physics;
2. senses Git;
3. fills the bowl from newly observed commits;
4. asks the configured brain for one proposal/expression;
5. applies deterministic policy and reflex fallback where required;
6. applies the legal action;
7. records mood, diary and wish;
8. updates lifecycle/stat bookkeeping;
9. stamps `last_tick`;
10. persists state;
11. publishes a new GUI snapshot only after persistence succeeds.

The LLM proposes. The deterministic harness decides and persists.

## Frozen organism boundary

Treat these modules as authoritative core unless a separately approved task
explicitly changes that boundary:

- `src/moss/clock.py`
- `src/moss/state.py`
- `src/moss/physics.py`
- `src/moss/policy.py`
- `src/moss/brain.py`
- `src/moss/senses.py`
- `src/moss/tick.py`
- `src/moss/llm.py`
- `src/moss/runtime.py`

UI work must compose the existing transaction rather than recreate organism
logic in QML or presentation code.

## Desktop lifecycle now in force

`MOSS-LIFECYCLE-01` makes Moss autonomous only while the habitat window is
open.

- Opening loads or hatches Moss but does not itself perform a tick.
- After a successful open, one wake tick is scheduled for 30-90 seconds.
- Later ticks use an independently drawn 6-14 minute triangular cadence with a
  10-minute mode.
- **Check in** is an optional immediate manual interaction. It invalidates the
  pending timer and restarts the steady cadence after the transaction finishes.
- At most one worker transaction may be active.
- Ticks are never queued and missed intervals are never replayed.
- Hard transaction/save failures retain the last confirmed projection and wait
  for the next normal cadence.
- Reflex fallback is a successful tick, not a lifecycle failure.
- Closing stops future scheduling and lets at most one already-running
  transaction finish.
- No daemon, tray process, startup service, persisted scheduler deadline or
  background life exists after the window closes.

`src/moss/lifecycle.py` owns cadence policy. `MossBridge` owns the one
single-shot Qt timer. QML owns presentation only.

## Current desktop composition

The accepted GUI is a responsive botanical desktop built around:

- `Habitat.qml` — the living terrarium and creature presentation.
- `FoodBowl.qml` — commit bowl and food tokens.
- `Home.qml` — masthead, habitat layout, Field Notes, vitals and the persistent
  caretaker/status footer.
- `Creature.qml` — visual action/mood presentation.

The footer currently presents persistent error state, brain status, activity,
the **Check in** action, and presentation-only details/disclosures. Those
controls must not mutate organism state except through the existing bridge
request that starts the authoritative tick transaction.

## Known operating limits

- One Moss process per home/repository. The runtime lock is process-local; there
  is no cross-process state lock.
- The existing Git sensor still conflates an empty repository history with Git
  failure. A healthy empty-repo distinction remains separate follow-on work.
- Local-model ticks can be slow. The worker boundary keeps the UI responsive and
  model failure degrades through the existing bounded reflex path.
- The autonomous scheduler has no visible countdown by design.

See `FAILURE_MAP.md` for lifecycle failure symptoms, diagnostics and safe
recovery.

## Validation discipline

Before claiming a change complete, run the relevant focused tests and the full
regression gate.

Typical full verification:

```powershell
python -m pytest -q -p no:cacheprovider
python -m compileall -q src
git diff --check
```

For GUI changes, keep native Windows runtime/visual acceptance separate from
automated test results. Tests prove bindings, authority boundaries and
behavioral invariants; they do not replace human visual acceptance.

Preserve unrelated working-tree changes. Do not reset, clean, stash, overwrite
or silently rewrite work outside the approved milestone.

## Next unfinished milestone: MOSS-UI-STATUS-01

The accepted `MOSS-LIFECYCLE-01` design explicitly names
`MOSS-UI-STATUS-01` as the next UI pass.

There is currently no dedicated `MOSS-UI-STATUS-01` specification or
implementation plan committed on `main`. Therefore the next task is **design
and contract definition first**, not production implementation.

The design pass should begin from the current lower caretaker/status surface in
`Home.qml` and the read-only bridge properties in `gui.py`. It may refine
how autonomous life, working state, brain/fallback state, hard errors and the
optional **Check in** interaction are communicated.

Unless Nolan explicitly broadens the milestone, STATUS-01 must preserve:

- the accepted botanical desktop composition;
- FoodBowl, Field Notes and vitals behavior;
- the autonomous lifecycle cadence and one-worker rule;
- the authoritative `MossRuntime.live_tick()` transaction;
- persistence and confirmed-snapshot semantics;
- QML as presentation-only;
- the current state schema, Git sensing, brain prompt/personality and organism
  actions.

A STATUS-01 visual redesign must not silently become a backend redesign.

## Recommended next agent task

1. Inspect `Home.qml`, `gui.py`, the GUI tests, the lifecycle spec and
   `FAILURE_MAP.md`.
2. Draft a bounded `MOSS-UI-STATUS-01` design/spec with explicit visual intent,
   authority boundaries, responsive behavior, failure-state presentation and
   acceptance criteria.
3. Present that design for Nolan's approval.
4. Only after approval, create the implementation plan and perform the smallest
   complete presentation change.
