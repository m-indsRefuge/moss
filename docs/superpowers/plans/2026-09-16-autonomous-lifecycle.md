# Moss Autonomous Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Moss live autonomously while the desktop habitat is open, with a random 30–90 second wake tick, a center-weighted 6–14 minute steady cadence, and optional manual **Check in** that resets the autonomous schedule.

**Architecture:** Add a pure cadence policy in `src/moss/lifecycle.py`; keep `MossRuntime.live_tick()` as the only authoritative life transaction; let `MossBridge` own one single-shot `QTimer` for session scheduling. Autonomous timer expiry and manual check-in converge on the same guarded worker path, with no overlapping ticks, queued ticks, catch-up bursts, or background process after the window closes.

**Tech Stack:** Python 3.12, PySide6 / Qt `QTimer` + `QThread`, QML, pytest.

**Spec:** `docs/superpowers/specs/2026-09-15-autonomous-lifecycle-design.md`

## Global Constraints

- Moss is autonomous only while the habitat window is open.
- Wake cadence is uniformly random from **30 to 90 seconds** after a successful open.
- Steady cadence is triangular from **6 to 14 minutes** with a **10-minute mode**.
- Randomness affects scheduling only; it must never affect tick semantics, physics, state, policy, sensing, or persistence.
- `MossRuntime.live_tick()` remains the only authoritative life transaction.
- QML remains presentation-only and must not own lifecycle timers.
- At most one lifecycle timer and one worker operation may be active.
- Manual **Check in** cancels the pending autonomous timer, triggers one immediate tick, then starts a fresh steady cadence.
- A hard tick/save failure preserves the last confirmed snapshot and schedules one normal later attempt; there is no rapid retry loop.
- A reflex fallback is a successful life tick, not a lifecycle failure.
- Closing stops future autonomous scheduling immediately; an in-flight operation may finish, after which the app closes with no reschedule.
- No persisted timer deadline, daemon, service, tray process, startup registration, catch-up ticks, new actions, new senses, new state schema, prompt tuning, or broader LLM role.
- Implementation follows TDD: verify RED before production code, then GREEN, then refactor only if needed.

---

## File Structure

- Create `src/moss/lifecycle.py` — pure cadence policy and constants only; no Qt, Git, filesystem, model, or persistence imports.
- Create `tests/test_lifecycle.py` — deterministic unit tests for wake/steady cadence bounds and injected RNG behavior.
- Modify `src/moss/gui.py` — session lifecycle owner; one single-shot timer; autonomous/manual convergence; close/failure rescheduling rules.
- Modify `tests/test_gui.py` — Qt integration coverage for wake scheduling, autonomous ticks, manual reset, failure recovery, overlap prevention, and shutdown.
- Modify `src/moss/qml/Home.qml` — minimal semantic copy change: ready action becomes `Check in`; no visual redesign.
- Modify `tests/test_architecture.py` — architecture tripwire that forbids lifecycle authority in QML.
- Create `FAILURE_MAP.md` — lifecycle failure boundaries, symptoms, diagnostics, propagation, safe recovery, and test references.
- Create `tests/test_failure_map.py` — lightweight documentation contract for required lifecycle failure entries.

---

### Task 1: Pure lifecycle cadence policy

**Files:**
- Create: `src/moss/lifecycle.py`
- Create: `tests/test_lifecycle.py`

**Interfaces:**
- Consumes: an injected RNG object implementing `uniform(a, b)` and `triangular(low, high, mode)`.
- Produces: `LifecycleCadence.wake_delay_ms() -> int` and `LifecycleCadence.steady_delay_ms() -> int`.

- [ ] **Step 1: Write failing cadence tests**

Create `tests/test_lifecycle.py`:

```python
from random import Random

from moss.lifecycle import (
    STEADY_MAX_S,
    STEADY_MIN_S,
    STEADY_MODE_S,
    WAKE_MAX_S,
    WAKE_MIN_S,
    LifecycleCadence,
)


class RecordingRng:
    def __init__(self):
        self.calls = []

    def uniform(self, low, high):
        self.calls.append(("uniform", low, high))
        return 42.5

    def triangular(self, low, high, mode):
        self.calls.append(("triangular", low, high, mode))
        return 601.25


def test_cadence_uses_exact_wake_and_steady_distribution_contracts():
    rng = RecordingRng()
    cadence = LifecycleCadence(rng=rng)

    assert cadence.wake_delay_ms() == 42_500
    assert cadence.steady_delay_ms() == 601_250
    assert rng.calls == [
        ("uniform", 30, 90),
        ("triangular", 360, 840, 600),
    ]
    assert (WAKE_MIN_S, WAKE_MAX_S) == (30, 90)
    assert (STEADY_MIN_S, STEADY_MODE_S, STEADY_MAX_S) == (360, 600, 840)


def test_seeded_cadence_is_reproducible_and_bounded():
    left = LifecycleCadence(rng=Random(1234))
    right = LifecycleCadence(rng=Random(1234))

    left_values = [left.wake_delay_ms(), *[left.steady_delay_ms() for _ in range(100)]]
    right_values = [right.wake_delay_ms(), *[right.steady_delay_ms() for _ in range(100)]]

    assert left_values == right_values
    assert 30_000 <= left_values[0] <= 90_000
    assert all(360_000 <= value <= 840_000 for value in left_values[1:])
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
python -m pytest tests/test_lifecycle.py -q -p no:cacheprovider
```

Expected: collection/import failure because `moss.lifecycle` does not yet exist.

- [ ] **Step 3: Implement the minimal pure cadence module**

Create `src/moss/lifecycle.py`:

```python
"""Pure scheduling cadence for one interactive Moss habitat session."""
from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Protocol

WAKE_MIN_S = 30
WAKE_MAX_S = 90
STEADY_MIN_S = 6 * 60
STEADY_MODE_S = 10 * 60
STEADY_MAX_S = 14 * 60


class RandomSource(Protocol):
    def uniform(self, a: float, b: float) -> float: ...
    def triangular(self, low: float, high: float, mode: float) -> float: ...


@dataclass
class LifecycleCadence:
    rng: RandomSource = field(default_factory=Random)

    def wake_delay_ms(self) -> int:
        return round(self.rng.uniform(WAKE_MIN_S, WAKE_MAX_S) * 1000)

    def steady_delay_ms(self) -> int:
        return round(
            self.rng.triangular(STEADY_MIN_S, STEADY_MAX_S, STEADY_MODE_S) * 1000
        )
```

- [ ] **Step 4: Run cadence tests and architecture tests**

Run:

```powershell
python -m pytest tests/test_lifecycle.py tests/test_architecture.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```powershell
git add src/moss/lifecycle.py tests/test_lifecycle.py
git commit -m "feat: add autonomous lifecycle cadence"
```

---

### Task 2: Add autonomous session scheduling to `MossBridge`

**Files:**
- Modify: `src/moss/gui.py`
- Modify: `tests/test_gui.py`

**Interfaces:**
- Consumes: `LifecycleCadence.wake_delay_ms()` and `LifecycleCadence.steady_delay_ms()`.
- Produces: one bridge-owned single-shot timer; autonomous timer expiry starts the same `MossRuntime.live_tick()` worker used by manual ticks.

- [ ] **Step 1: Add a deterministic test cadence helper to `tests/test_gui.py`**

Add near the existing test helpers:

```python
class ScriptedCadence:
    def __init__(self, *, wake_ms=10, steady_ms=10_000):
        self.wake_ms = wake_ms
        self.steady_ms = steady_ms
        self.wake_calls = 0
        self.steady_calls = 0

    def wake_delay_ms(self):
        self.wake_calls += 1
        return self.wake_ms

    def steady_delay_ms(self):
        self.steady_calls += 1
        return self.steady_ms
```

- [ ] **Step 2: Write the failing autonomous-open test**

Add:

```python
def test_successful_open_schedules_one_wake_tick_then_one_steady_timer(app, tmp_path):
    cadence = ScriptedCadence(wake_ms=20, steady_ms=10_000)
    runtime = MossRuntime(tmp_path, clock=SimClock(), senses=FixtureSenses([]))
    bridge = MossBridge(runtime, cadence=cadence)
    actions = QSignalSpy(bridge.tickCompleted)

    bridge.open()
    until(lambda: bridge.ready and not bridge.busy)

    assert not bridge.hasTick
    assert actions.count() == 0
    assert cadence.wake_calls == 1
    assert cadence.steady_calls == 0

    until(lambda: actions.count() == 1)
    assert bridge.hasTick
    assert cadence.steady_calls == 1
    assert bridge._life_timer.isActive()

    bridge.requestClose()
    assert not bridge._life_timer.isActive()
    bridge.finish_shutdown()
```

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```powershell
python -m pytest tests/test_gui.py::test_successful_open_schedules_one_wake_tick_then_one_steady_timer -q -p no:cacheprovider
```

Expected: FAIL because `MossBridge` has no `cadence` constructor argument and no lifecycle timer.

- [ ] **Step 4: Add the bridge-owned single-shot timer**

Update `src/moss/gui.py` imports:

```python
from moss.lifecycle import LifecycleCadence
```

Change the constructor signature and add timer setup:

```python
def __init__(self, runtime: MossRuntime, *, cadence=None):
    super().__init__()
    self._runtime = runtime
    self._cadence = cadence if cadence is not None else LifecycleCadence()
    self._snapshot = None
    self._job = None
    self._is_tick = False
    self._closing = False
    self._error = ""
    self._life_timer = QTimer(self)
    self._life_timer.setSingleShot(True)
    self._life_timer.timeout.connect(self._autonomous_tick)
```

Add these helpers:

```python
def _schedule_wake(self):
    if self.ready and not self.busy and not self._closing:
        self._life_timer.start(self._cadence.wake_delay_ms())


def _schedule_steady(self):
    if self.ready and not self.busy and not self._closing:
        self._life_timer.start(self._cadence.steady_delay_ms())


@Slot()
def _autonomous_tick(self):
    if self.ready and not self.busy and not self._closing:
        self._start(True)
```

In `_completed()`, capture whether the finished operation was a tick before clearing `_job`, then schedule according to operation type:

```python
was_tick = self._is_tick
...
self._job = None
job.deleteLater()
self.activityChanged.emit()
if self._closing:
    self.closeReady.emit()
elif was_tick:
    self._schedule_steady()
elif self.ready:
    self._schedule_wake()
```

The scheduling branch must run even when a tick worker completed with `job.error`, because the spec requires normal-cadence recovery after hard transaction failure.

- [ ] **Step 5: Run the autonomous-open test**

Run:

```powershell
python -m pytest tests/test_gui.py::test_successful_open_schedules_one_wake_tick_then_one_steady_timer -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 6: Run existing GUI regression tests**

Run:

```powershell
python -m pytest tests/test_gui.py -q -p no:cacheprovider
```

Expected: PASS. Existing manual tests complete well before the production 30-second minimum wake delay unless they inject `ScriptedCadence`.

- [ ] **Step 7: Commit Task 2**

```powershell
git add src/moss/gui.py tests/test_gui.py
git commit -m "feat: schedule autonomous Moss life ticks"
```

---

### Task 3: Manual Check in, failure recovery, and shutdown guards

**Files:**
- Modify: `src/moss/gui.py`
- Modify: `tests/test_gui.py`

**Interfaces:**
- Consumes: bridge lifecycle timer and existing `_start(True)` worker path.
- Produces: manual tick reset semantics, no-overlap behavior, close-time invalidation, normal-cadence recovery after failed ticks.

- [ ] **Step 1: Write the failing manual-reset test**

Add:

```python
def test_manual_check_in_cancels_pending_wake_and_resets_steady_schedule(app, tmp_path):
    cadence = ScriptedCadence(wake_ms=10_000, steady_ms=10_000)
    bridge = MossBridge(
        MossRuntime(tmp_path, clock=SimClock(), senses=FixtureSenses([])),
        cadence=cadence,
    )
    actions = QSignalSpy(bridge.tickCompleted)

    bridge.open()
    until(lambda: bridge.ready and not bridge.busy)
    assert bridge._life_timer.isActive()
    assert cadence.wake_calls == 1

    bridge.requestTick()
    assert not bridge._life_timer.isActive()
    until(lambda: actions.count() == 1 and not bridge.busy)

    assert cadence.steady_calls == 1
    assert bridge._life_timer.isActive()
    bridge.requestClose()
    bridge.finish_shutdown()
```

- [ ] **Step 2: Write the failing hard-failure reschedule test**

Add:

```python
def test_failed_autonomous_tick_preserves_snapshot_and_reschedules_normally(app, tmp_path, monkeypatch):
    cadence = ScriptedCadence(wake_ms=10_000, steady_ms=10_000)
    runtime = MossRuntime(tmp_path, clock=SimClock(), senses=FixtureSenses([]))
    bridge = MossBridge(runtime, cadence=cadence)

    bridge.open()
    until(lambda: bridge.ready and not bridge.busy)
    confirmed = bridge._snapshot
    before = runtime.state_path.read_bytes()

    def failed_save(*args):
        raise OSError("blocked")

    monkeypatch.setattr("moss.runtime.save", failed_save)
    bridge.requestTick()
    until(lambda: not bridge.busy)

    assert bridge.error
    assert bridge._snapshot is confirmed
    assert runtime.state_path.read_bytes() == before
    assert cadence.steady_calls == 1
    assert bridge._life_timer.isActive()

    bridge.requestClose()
    bridge.finish_shutdown()
```

- [ ] **Step 3: Strengthen the existing overlap/close test**

Construct that test's bridge with a long scripted cadence and add assertions around close:

```python
cadence = ScriptedCadence(wake_ms=10_000, steady_ms=10_000)
bridge = MossBridge(runtime, cadence=cadence)
...
bridge.requestClose()
assert bridge.closing
assert not bridge._life_timer.isActive()
...
assert cadence.steady_calls == 0  # completion while closing never reschedules
```

- [ ] **Step 4: Run the three lifecycle-guard tests and verify RED**

Run:

```powershell
python -m pytest \
  tests/test_gui.py::test_manual_check_in_cancels_pending_wake_and_resets_steady_schedule \
  tests/test_gui.py::test_failed_autonomous_tick_preserves_snapshot_and_reschedules_normally \
  tests/test_gui.py::test_worker_keeps_event_loop_live_rejects_overlap_and_defers_close \
  -q -p no:cacheprovider
```

Expected: at least the manual-reset and shutdown-timer assertions fail before production changes.

- [ ] **Step 5: Implement manual timer cancellation and close invalidation**

Update `requestTick()`:

```python
@Slot()
def requestTick(self):
    if self.ready and not self.busy and not self._closing:
        self._life_timer.stop()
        self._start(True)
```

Update `open()` so an explicit retry/open cannot leave a stale autonomous timer active:

```python
@Slot()
def open(self):
    if not self.busy and not self._closing:
        self._life_timer.stop()
        self._start(False)
```

Update `requestClose()` and defensive shutdown:

```python
@Slot()
def requestClose(self):
    self._life_timer.stop()
    self._closing = True
    self.activityChanged.emit()
    if not self.busy:
        self.closeReady.emit()


def finish_shutdown(self):
    self._life_timer.stop()
    if self._job is not None:
        self._job.wait()
```

Do not add retry counters, pending-tick flags, queues, or catch-up logic.

- [ ] **Step 6: Run focused lifecycle guard tests**

Run the same command from Step 4.

Expected: PASS.

- [ ] **Step 7: Run all GUI tests**

```powershell
python -m pytest tests/test_gui.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 8: Commit Task 3**

```powershell
git add src/moss/gui.py tests/test_gui.py
git commit -m "feat: guard autonomous lifecycle interactions"
```

---

### Task 4: Minimum UI semantic correction and QML authority tripwire

**Files:**
- Modify: `src/moss/qml/Home.qml`
- Modify: `src/moss/gui.py`
- Modify: `tests/test_gui.py`
- Modify: `tests/test_architecture.py`

**Interfaces:**
- Consumes: existing `tickButton`, `bridge.requestTick()`, `bridge.activity`.
- Produces: optional manual action labeled **Check in**; no visible countdown; no QML lifecycle timer.

- [ ] **Step 1: Write the failing architecture tripwire**

Add QML scanning to `tests/test_architecture.py`:

```python
QML = SRC / "qml"


def test_qml_does_not_own_lifecycle_timers():
    offenders = []
    for f in sorted(QML.glob("*.qml")):
        text = f.read_text(encoding="utf-8")
        if "Timer {" in text:
            offenders.append(f.name)
    assert not offenders, f"Lifecycle Timer found in QML: {offenders}"
```

This test should already pass and acts as a permanent architecture tripwire.

- [ ] **Step 2: Add a failing semantic assertion to the existing habitat button test**

After `bridge.open()` completes, add:

```python
button = window.findChild(QQuickItem, "tickButton")
assert button.property("text") == "Check in"
assert bridge.activity == "Moss is awake and watching the repository."
```

- [ ] **Step 3: Run the focused semantic test and verify RED**

```powershell
python -m pytest tests/test_gui.py::test_habitat_button_publishes_saved_outcome_and_disclosures_do_not_tick -q -p no:cacheprovider
```

Expected: FAIL because current UI still says `Live a tick` and current activity says ticks happen only when asked.

- [ ] **Step 4: Make only the approved copy changes**

In `src/moss/qml/Home.qml`, change the ready-state button text expression from:

```qml
text: bridge.busy ? "Working…" : bridge.ready ? "Live a tick" : "Open home"
```

to:

```qml
text: bridge.busy ? "Working…" : bridge.ready ? "Check in" : "Open home"
```

In `src/moss/gui.py`, change the idle-ready `activity` return value to:

```python
return "Moss is awake and watching the repository." if self.ready else "Moss has not loaded."
```

Do not redesign the status strip in this task. `MOSS-UI-STATUS-01` remains follow-on work.

- [ ] **Step 5: Run semantic, architecture, and presentation tests**

```powershell
python -m pytest tests/test_architecture.py tests/test_gui.py tests/test_field_notes_qml.py tests/test_food_bowl_qml.py tests/test_vitals_qml.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```powershell
git add src/moss/qml/Home.qml src/moss/gui.py tests/test_gui.py tests/test_architecture.py
git commit -m "feat: present manual lifecycle check in"
```

---

### Task 5: Add lifecycle failure map and documentation contract

**Files:**
- Create: `FAILURE_MAP.md`
- Create: `tests/test_failure_map.py`

**Interfaces:**
- Consumes: lifecycle failure cases defined by the approved spec.
- Produces: durable operational documentation for diagnosis and safe recovery.

- [ ] **Step 1: Write the failing documentation contract**

Create `tests/test_failure_map.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAILURE_MAP = ROOT / "FAILURE_MAP.md"


def test_failure_map_covers_autonomous_lifecycle_boundaries():
    text = FAILURE_MAP.read_text(encoding="utf-8")
    for marker in (
        "Autonomous timer inactive",
        "Timer fires while worker is active",
        "Duplicate or overlapping tick",
        "Close during an in-flight tick",
        "Model latency exceeds cadence",
        "Reflex fallback versus hard failure",
        "Save failure during autonomous tick",
        "Manual Check in invalidates timer",
        "Suspend or resume without catch-up",
        "Multiple Moss processes",
    ):
        assert marker in text
```

- [ ] **Step 2: Run and verify RED**

```powershell
python -m pytest tests/test_failure_map.py -q -p no:cacheprovider
```

Expected: FAIL because `FAILURE_MAP.md` does not yet exist.

- [ ] **Step 3: Create the lifecycle failure map**

Create `FAILURE_MAP.md` with a short introduction and one subsection for each marker above. Every subsection must contain these exact fields:

```markdown
### <failure name>
- **Observable symptom:** ...
- **Likely causes:** ...
- **First diagnostics:** ...
- **Propagation risk:** ...
- **Safe recovery:** ...
- **Do not:** ...
- **Related tests:** ...
```

Use the following required recovery rules:

- Timer inactivity: inspect bridge readiness, closing state, timer activity, and cadence calls; do not manually mutate `moss.state.json`.
- Worker already active / duplicate tick: verify the single-shot timer and `busy` guard; do not add a queue or second worker.
- Close in flight: allow the single transaction to finish; never schedule another interval while closing.
- Model latency: let the current worker finish; there is no catch-up tick because the next timer starts only after completion.
- Reflex fallback: treat it as a successful tick; distinguish it from `bridge.error` transaction failure.
- Save failure: retain the confirmed snapshot and wait for the next normal cadence; do not rapid-retry.
- Manual Check in: stop the old timer before starting the immediate tick; schedule a fresh steady delay only after completion.
- Suspend/resume: never replay elapsed intervals; elapsed physics is handled inside the next real tick.
- Multiple processes: maintain the existing one-process-per-home rule; do not introduce inter-process coordination in this milestone.

- [ ] **Step 4: Run documentation contract**

```powershell
python -m pytest tests/test_failure_map.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```powershell
git add FAILURE_MAP.md tests/test_failure_map.py
git commit -m "docs: map autonomous lifecycle failures"
```

---

### Task 6: Full verification and native autonomous-life validation

**Files:**
- No planned production changes.
- Modify only if verification exposes a genuine defect; if a core architecture change is required, stop and return to the approved spec rather than broadening scope silently.

**Interfaces:**
- Consumes: all Task 1–5 deliverables.
- Produces: evidence that MOSS-LIFECYCLE-01 satisfies the spec and preserves all existing frozen UI/component behavior.

- [ ] **Step 1: Run focused lifecycle and architecture tests**

```powershell
python -m pytest tests/test_lifecycle.py tests/test_failure_map.py tests/test_architecture.py tests/test_gui.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 2: Run the full suite**

```powershell
python -m pytest -q -p no:cacheprovider
```

Expected: PASS with zero failures.

- [ ] **Step 3: Run compile and diff hygiene checks**

```powershell
python -m compileall -q src
git diff --check 71b1596d78a0ec2c028e9c37df7fc0b4ea10df51...HEAD
```

Expected: both commands exit successfully with no output requiring action.

- [ ] **Step 4: Confirm the implementation diff is scoped**

```powershell
git diff --name-only 71b1596d78a0ec2c028e9c37df7fc0b4ea10df51...HEAD
```

Expected implementation-related paths are limited to:

```text
FAILURE_MAP.md
src/moss/lifecycle.py
src/moss/gui.py
src/moss/qml/Home.qml
tests/test_lifecycle.py
tests/test_gui.py
tests/test_architecture.py
tests/test_failure_map.py
```

The already-approved spec and this plan will also appear on the branch under `docs/superpowers/`.

- [ ] **Step 5: Native Windows runtime test with short validation cadence**

Do not alter production cadence constants for this check. Add a temporary test-only/local harness or instantiate `MossBridge` with a scripted cadence in a disposable validation path if an accelerated visual check is needed. The production executable must continue using `LifecycleCadence()` with 30–90 second wake and 6–14 minute steady timing.

For the actual production-path acceptance run, launch:

```powershell
moss home --brain llm --model qwen3:8b --timeout 120
```

Observe at least the first autonomous wake event without clicking **Check in**. Confirm:

1. persisted state appears immediately on open;
2. the button says **Check in**;
3. Moss autonomously performs one life tick within 30–90 seconds;
4. the UI remains responsive during model work;
5. the resulting action animation, diary/thought, bowl, vitals, and status update from the saved tick;
6. clicking **Check in** later triggers one immediate tick and does not produce a second near-back-to-back autonomous tick;
7. closing the habitat leaves no Moss process running.

- [ ] **Step 6: Final verification before completion claim**

Re-run after any defect fix:

```powershell
python -m pytest -q -p no:cacheprovider
python -m compileall -q src
git diff --check 71b1596d78a0ec2c028e9c37df7fc0b4ea10df51...HEAD
```

Do not call MOSS-LIFECYCLE-01 complete until fresh output confirms all three gates and the native autonomous wake has been observed.

- [ ] **Step 7: Prepare integration**

After Nolan accepts the native behavior, create the PR with a summary of cadence, authority boundaries, failure behavior, validation evidence, and the explicit statement that QML remains presentation-only. Merge only after final approval.
