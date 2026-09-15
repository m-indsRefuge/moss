# Moss Autonomous Lifecycle Design

**Date:** 2026-09-15  
**Project:** Moss  
**Design ID:** MOSS-LIFECYCLE-01  
**Status:** Approved design; implementation not yet started

## Purpose

Moss is an interactive desktop pet that lives in a Git repository while the user is actively working with that repository. The current implementation only advances Moss when the user explicitly requests a live tick. This design changes that product behavior so Moss lives autonomously while his habitat window is open.

The user must not need to click a button for Moss to sense Git, update his drives, consult his brain, act, write a diary entry, or persist a new life state.

Moss does **not** need to continue living after the habitat window is closed. Closing the desktop application ends the active session. There is no background daemon, tray process, startup service, or catch-up process.

## Product intent

The experience should feel like a small living creature accompanying the user while they work on a repository, not like a simulation that only runs when commanded.

Autonomy must remain bounded and legible:

- Moss is autonomous only while the habitat window is open.
- Each lived moment remains one existing authoritative tick transaction.
- Autonomous timing is irregular enough to feel organic but bounded enough to prevent runaway model calls.
- Manual interaction remains available as an optional immediate check-in.
- The scheduler never creates overlapping, queued, or catch-up ticks.
- The QML layer remains presentation-only and never acquires simulation authority.

## Existing trusted transaction

This design preserves the existing life transaction implemented by `MossRuntime.live_tick()` and `tick()`.

One tick continues to perform the same sequence:

1. Calculate elapsed-time decay.
2. Sense Git relative to the previous completed tick.
3. Fill the bowl with newly observed commits.
4. Ask the configured brain for one proposed action and expression.
5. Apply the deterministic policy veto and reflex fallback when required.
6. Apply the legal action to deterministic drives and statistics.
7. Record mood, diary, and wish through the expression channel.
8. Update lifecycle bookkeeping such as longest quiet period.
9. Stamp `last_tick` last.
10. Persist the new state.
11. Publish the new snapshot only after persistence succeeds.

The autonomous lifecycle does not duplicate or reimplement any of these responsibilities. It decides only **when** the existing transaction should run.

## Chosen architecture

### 1. Cadence policy: `src/moss/lifecycle.py`

Add a small pure-Python lifecycle cadence unit with no knowledge of Qt, QML, Git, persistence, state files, or the LLM.

Its only responsibility is to produce bounded delays.

The cadence policy exposes two delay classes:

- **Wake delay:** uniformly random from 30 to 90 seconds after a successful application open.
- **Steady delay:** triangularly distributed from 6 to 14 minutes, with a 10-minute mode, after each completed life tick.

The steady cadence is therefore center-weighted rather than uniformly distributed. Python's triangular distribution is an appropriate implementation because it keeps hard minimum and maximum bounds while favoring values near the 10-minute center.

The random source must be injectable. Production may use a normal pseudo-random generator; tests must be able to supply a deterministic or scripted source so scheduling behavior is reproducible.

The cadence policy returns durations only. It never calls `live_tick()` and never owns a timer.

### 2. Session orchestration: `MossBridge`

`MossBridge` becomes the owner of the active desktop-session lifecycle.

It owns one single-shot `QTimer` for autonomous scheduling. There is no repeating interval timer.

The bridge remains responsible for starting worker transactions and publishing confirmed snapshots. Autonomous timer expiry and manual check-in converge on the same guarded tick-start path.

The lifecycle boundary is:

```text
Cadence policy        = when
MossBridge            = session orchestration
MossRuntime.live_tick = authoritative transaction
tick.py               = organism logic
QML                    = presentation only
```

### 3. Runtime and organism core

`MossRuntime.live_tick()`, `tick.py`, physics, policy, senses, and brain boundaries remain authoritative and interface-independent.

Scheduling must not be moved into `MossRuntime` because a desktop-window session is a presentation/session concern rather than an organism-core concern.

Scheduling must not be moved into QML because QML must never drive simulation state.

## Session state machine

The active desktop session follows this conceptual state machine:

```text
OPENING
  |
  v
AWAKE_WAITING
  | timer expiry or manual Check in
  v
TICKING
  | success or failure
  v
AWAKE_WAITING
```

A close request may occur from **OPENING**, **AWAKE_WAITING**, or **TICKING**. It immediately moves the session into closing behavior: pending timers are invalidated, no future lifecycle work may be scheduled, and any one already-running worker operation is allowed to finish under the existing shutdown contract.

These states may be represented explicitly or through existing bridge state plus clear lifecycle guards, but the observable behavior must match this state machine.

## Startup behavior

1. The application starts exactly as it does today.
2. `bridge.open()` loads or hatches Moss using the existing worker transaction.
3. Opening alone must not perform a life tick.
4. If opening succeeds and the bridge has a confirmed snapshot, Moss becomes ready.
5. Only after readiness is confirmed, schedule one wake timer for a uniformly random delay between 30 and 90 seconds.
6. When that timer expires, start exactly one autonomous `live_tick()` transaction.
7. After that life tick completes, schedule the normal steady-state cadence.

If opening fails and there is no confirmed snapshot, autonomous lifecycle scheduling must not begin.

If the user requested close while opening was still in flight, completion of that open operation must not schedule a wake timer.

## Steady autonomous cadence

After every completed life-tick attempt, draw a new independent steady delay from a triangular distribution bounded at 6 and 14 minutes with a 10-minute mode.

The expected experience is irregular but bounded. Moss may live again after, for example, roughly 7 minutes, then 11 minutes, then 9 minutes. The user should not perceive a fixed metronome.

The exact scheduler distribution must not affect organism determinism. The tick itself continues to use elapsed wall time since the previous successfully persisted `last_tick`, so changing cadence frequency does not convert decay into "per tick" decay.

## One timer, one worker, one tick

The scheduler must guarantee all of the following:

- At most one autonomous timer is active.
- At most one worker operation is active.
- A timer expiry clears or consumes its pending schedule before attempting to start a tick.
- If the bridge is already busy or closing, no second tick is queued.
- No missed interval is replayed later.
- No burst of catch-up ticks occurs after application stalls, model latency, operating-system suspend/resume, or close/reopen.
- The next steady interval is scheduled only after the current tick attempt has completed.
- Completion of any worker operation while closing never schedules new lifecycle work.

## Manual interaction: Check in

Keep the current manual tick capability, but change its product meaning.

The user-facing action becomes **Check in** rather than the mechanism required to make Moss live.

When the user requests a manual check-in while Moss is ready and idle:

1. Cancel the currently pending autonomous timer.
2. Start one immediate tick through the same guarded worker path used by autonomous life.
3. When that tick attempt completes, draw and schedule a fresh steady 6-to-14-minute interval.

This prevents a stale autonomous timer from firing immediately after a manual interaction and creating back-to-back model calls or diary entries.

If Moss is busy or closing, the existing no-queue behavior remains: the request does not accumulate into a later surprise tick.

The bridge API may retain the internal name `requestTick()` during this change if that avoids unnecessary churn, but the UI semantics must change from `Live a tick` to `Check in`.

## Failure behavior

### LLM failure or unusable response

Existing brain behavior remains unchanged. The LLM receives at most the existing bounded number of attempts. If it cannot produce a usable legal decision, deterministic reflex fallback supplies the action.

A reflex fallback is a completed life tick, not a lifecycle failure. Normal steady scheduling continues.

### Transaction or save failure

If an autonomous or manual tick fails before a new state can be successfully persisted:

- Do not publish the failed tick's proposed snapshot.
- Keep displaying the last confirmed snapshot.
- Surface the existing error state to the UI.
- Do not perform an immediate automatic retry.
- Schedule the next attempt using a normal fresh steady 6-to-14-minute delay, unless the session is closing.

This avoids retry storms against the filesystem, Git, or local model.

### Open failure

If the initial open operation fails without establishing a confirmed snapshot:

- Do not begin autonomous scheduling.
- Preserve the existing open-error presentation.
- A user-triggered retry/open path may continue to use existing behavior.

## Shutdown behavior

Closing the habitat ends autonomous life for that session.

On close request:

1. Stop and invalidate the pending lifecycle timer immediately, if one exists.
2. Set the bridge closing state as today.
3. If no worker transaction is running, allow the application to close.
4. If an open or tick transaction is already in flight, allow that single transaction to finish using the existing shutdown contract, then close.
5. Do not schedule a wake or steady timer after any completion that occurred while closing.

The application must not leave a background timer, worker, service, daemon, or process alive after the window exits.

## Reopen behavior

A new application launch starts a new interactive session.

Moss loads the last successfully persisted state immediately, then draws a new uniform 30-to-90-second wake delay.

The scheduler does not persist its pending deadline to `moss.state.json` and does not reconstruct missed life moments from the period when the application was closed.

Elapsed-time physics already accounts for real time since the previous persisted tick when the next tick eventually occurs.

## UI boundary

This architecture is not a visual redesign. The dedicated `MOSS-UI-STATUS-01` pass remains separate.

The lifecycle implementation should make only the minimum semantic UI correction required by the behavior change:

- Replace `Live a tick` with `Check in` for the ready manual-action state.
- Remove or replace wording that says ticks happen only when the user asks.
- Preserve `Working...` and open/retry semantics unless implementation evidence requires a more precise label.

The habitat should not expose a visible scheduler countdown by default. Moss should feel alive, not like a timer dashboard.

A small lifecycle/status property may be exposed by the bridge if needed for clear status presentation or testing, but the UI must not gain simulation authority.

## Expected implementation surface

The implementation plan should expect changes primarily in:

- `src/moss/lifecycle.py` — new pure cadence policy.
- `src/moss/gui.py` — single-shot session scheduler and convergence of autonomous/manual tick paths.
- `src/moss/qml/Home.qml` — minimum wording change from manual life support to optional Check in.
- tests for lifecycle cadence and GUI scheduling behavior.
- `FAILURE_MAP.md` — document new lifecycle failure boundaries and diagnostics.

No change is expected to the authoritative semantics in:

- `src/moss/tick.py`
- `src/moss/physics.py`
- `src/moss/policy.py`
- Git observation rules
- state schema
- LLM prompt/personality

If implementation reveals that one of those core areas must change, stop and re-evaluate the architecture rather than silently broadening scope.

## Testing strategy

Implementation must follow TDD and include deterministic lifecycle tests.

### Cadence policy tests

Verify that:

- Wake delays are never below 30 seconds or above 90 seconds.
- The wake draw uses the configured uniform bounds.
- Steady delays are never below 6 minutes or above 14 minutes.
- The steady draw uses a triangular distribution with a 10-minute mode.
- An injected deterministic/scripted random source produces reproducible delays.
- The cadence module has no Qt, QML, Git, model, persistence, or filesystem side effects.

Tests should prefer verifying the configured bounds/mode and scripted draws over fragile statistical assertions about a finite sample.

### Bridge/session tests

Verify that:

- Successful open loads state but does not itself run a life tick.
- Successful open schedules exactly one wake timer.
- Close requested during opening prevents wake scheduling after the open worker finishes.
- The first autonomous timer produces exactly one tick.
- A completed tick schedules exactly one new steady timer.
- Manual Check in cancels the pending timer, starts one immediate tick, and resets the steady schedule after completion.
- Busy state prevents overlapping and queued ticks.
- Closing cancels future autonomous scheduling.
- Close during an in-flight tick waits for that one operation and schedules nothing afterwards.
- A failed tick leaves the last confirmed snapshot intact and schedules one ordinary next interval rather than retrying immediately.
- Reflex fallback still counts as a normal completed tick and continues scheduling.
- Reopening begins with a fresh wake delay rather than a persisted pending schedule.

### Existing regression gates

The existing full test suite must continue to pass, including GUI reachability, presentation-only disclosure controls, persistence behavior, FoodBowl, Field Notes, vitals, and animation-side-effect boundaries.

Native Windows visual/runtime validation must confirm that autonomous ticks update Moss without user clicks and that the application remains responsive during local-model work.

## Failure-aware engineering requirements

`FAILURE_MAP.md` must gain lifecycle-specific entries for at least:

- autonomous timer fails to schedule or is unexpectedly inactive;
- timer fires while a worker is already active;
- duplicate/overlapping tick prevention;
- close while open or autonomous tick is in flight;
- model latency longer than the scheduled interval;
- local-model fallback versus hard transaction failure;
- state-save failure during an autonomous tick;
- timer invalidation during manual Check in;
- application suspend/resume without catch-up bursts;
- prohibition on multiple Moss processes writing the same home.

Each entry should include observable symptoms, likely causes, first diagnostics, propagation risk, safe recovery, and related tests.

## Non-goals

MOSS-LIFECYCLE-01 does not add:

- background life after the habitat window closes;
- Windows services, tray apps, startup registration, or daemons;
- persisted timer deadlines;
- catch-up ticks for time spent closed;
- multiple concurrent Moss processes;
- new Git senses or broader repository access;
- new organism actions;
- new state schema fields unless implementation demonstrates they are strictly necessary and the design is revisited;
- new LLM prompts, personality tuning, memory systems, RAG, embeddings, or autonomous coding;
- QML-owned lifecycle timers;
- a visible countdown dashboard;
- the full STATUS-01 visual redesign.

## Architectural invariants

The implementation is acceptable only if these remain true:

1. Deterministic Python remains the sole authority over state, physics, policy, persistence, and legal actions.
2. The LLM remains a proposal/expression component and cannot directly mutate state.
3. QML remains presentation-only.
4. There is only one authoritative `live_tick()` transaction.
5. There is at most one life transaction in flight.
6. New state is published only after successful persistence.
7. Randomness affects scheduling time only, never tick semantics or organism physics.
8. Autonomous life exists only for the lifetime of the desktop habitat session.
9. Manual Check in is optional and resets the autonomous cadence rather than becoming a second lifecycle.
10. Failures do not produce rapid retry loops or catch-up bursts.

## Acceptance criteria

MOSS-LIFECYCLE-01 is complete when all of the following are demonstrated:

- Opening Moss shows the persisted state immediately without performing a tick.
- Without any user interaction, Moss performs his first autonomous life tick within the configured 30-to-90-second wake window.
- Subsequent autonomous life moments are scheduled independently in the bounded 6-to-14-minute triangular cadence with a 10-minute mode.
- A user can request an immediate Check in, after which the autonomous cadence restarts cleanly.
- Autonomous and manual triggers can never overlap or queue surprise ticks.
- Hard tick failures preserve the last confirmed state and resume only on a normal later cadence.
- Closing the habitat prevents all future autonomous ticks and leaves no background lifecycle process.
- Existing deterministic transaction, policy, persistence, model fallback, and QML authority boundaries remain intact.
- Lifecycle failure surfaces are documented in `FAILURE_MAP.md`.
- Focused lifecycle tests, full regression suite, compile checks, diff checks, and native Windows runtime validation pass.

## Follow-on work

Once MOSS-LIFECYCLE-01 is accepted and integrated, resume the paused UI sequence with `MOSS-UI-STATUS-01`.

That pass may then redesign the lower caretaker console around the new reality that Moss is already alive autonomously, with **Check in** presented as an optional interaction rather than the source of life.
