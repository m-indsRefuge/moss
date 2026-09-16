# Moss Failure Map

This document records important failure boundaries for the Moss desktop
habitat. Moss's deterministic Python runtime remains authoritative for
state, persistence, Git sensing, actions, and lifecycle transactions.

The autonomous scheduler exists only while the habitat application is
open. It uses one single-shot timer, never queues catch-up ticks, and
always delegates real life transactions to `MossRuntime.live_tick()`.

## Autonomous lifecycle

### Autonomous timer inactive
- **Observable symptom:** Moss opens successfully but no autonomous tick occurs after the expected wake or steady interval.
- **Likely causes:** Bridge is not ready, the bridge is closing, the timer was stopped, cadence was not scheduled after completion, or the event loop is no longer running.
- **First diagnostics:** Inspect `bridge.ready`, `bridge.busy`, `bridge.closing`, `_life_timer.isActive()`, and cadence-call evidence.
- **Propagation risk:** Moss remains visually available but does not autonomously advance until another valid tick occurs.
- **Safe recovery:** Confirm the habitat event loop is active and reopen the habitat if necessary so a fresh wake interval is scheduled.
- **Do not:** Do not manually mutate `moss.state.json`, invent a persisted timer deadline, or force a catch-up tick.
- **Related tests:** `test_successful_open_schedules_one_wake_tick_then_one_steady_timer`.

### Timer fires while worker is active
- **Observable symptom:** A timer event occurs while an open or tick worker has not completed.
- **Likely causes:** Event-loop timing, unusually long Git/model latency, or an incorrectly retained timer.
- **First diagnostics:** Inspect `bridge.busy`, `_job`, `_life_timer`, and worker completion ordering.
- **Propagation risk:** Without the guard, two transactions could race over the same persisted state.
- **Safe recovery:** Let the existing worker finish; the bridge busy guard rejects another transaction and completion schedules the next fresh interval.
- **Do not:** Do not add a second worker, pending-tick flag, queue, or overlapping transaction.
- **Related tests:** `test_worker_keeps_event_loop_live_rejects_overlap_and_defers_close`.

### Duplicate or overlapping tick
- **Observable symptom:** More than one life transaction appears to start from the same habitat session at once.
- **Likely causes:** A broken busy guard, multiple scheduling mechanisms, or manual and autonomous triggers both being accepted.
- **First diagnostics:** Check `_start()`, `requestTick()`, `_autonomous_tick()`, `_job`, and the single-shot timer configuration.
- **Propagation risk:** Concurrent persistence could corrupt or overwrite authoritative organism state.
- **Safe recovery:** Preserve exactly one `_Operation`; reject all other tick requests until it completes.
- **Do not:** Do not create a transaction queue or parallelize `MossRuntime.live_tick()`.
- **Related tests:** `test_worker_keeps_event_loop_live_rejects_overlap_and_defers_close`.

### Close during an in-flight tick
- **Observable symptom:** The window is asked to close while Moss is still sensing, consulting the brain, or saving state.
- **Likely causes:** Normal user shutdown during a slow transaction.
- **First diagnostics:** Inspect `bridge.closing`, `bridge.busy`, `_job`, `closeReady`, and lifecycle timer activity.
- **Propagation risk:** Killing the worker during persistence could leave the transaction incomplete.
- **Safe recovery:** Stop the lifecycle timer immediately, allow the single in-flight transaction to finish, then emit close readiness without rescheduling.
- **Do not:** Do not cancel a transaction mid-save and do not schedule another interval while closing.
- **Related tests:** `test_worker_keeps_event_loop_live_rejects_overlap_and_defers_close`.

### Model latency exceeds cadence
- **Observable symptom:** A model-backed tick takes longer than a normal lifecycle interval.
- **Likely causes:** Local model latency, model retry behavior, system load, or slow repository sensing.
- **First diagnostics:** Inspect worker duration, brain status, decision attempts, and whether the bridge remains busy.
- **Propagation risk:** Poor scheduling could otherwise accumulate overdue ticks.
- **Safe recovery:** Let the current worker finish; only after completion is a new steady timer started.
- **Do not:** Do not calculate or replay missed intervals and do not run catch-up ticks.
- **Related tests:** `test_worker_keeps_event_loop_live_rejects_overlap_and_defers_close`.

### Reflex fallback versus hard failure
- **Observable symptom:** Moss may complete a tick using deterministic reflex behavior, or may instead expose `bridge.error` with no new visible snapshot.
- **Likely causes:** Reflex fallback follows unusable model responses or model exceptions; hard failure follows transaction failures such as persistence errors.
- **First diagnostics:** Compare `brainStatus`, `usedFallback`, `decisionAttempts`, `bridge.error`, and whether `tickCompleted` was emitted.
- **Propagation risk:** Confusing fallback with failure could cause unnecessary retries or discard a valid completed tick.
- **Safe recovery:** Treat reflex fallback as a successful tick; treat `bridge.error` as transaction failure while retaining the last confirmed projection.
- **Do not:** Do not rapid-retry a reflex fallback or publish an unpersisted failed transaction.
- **Related tests:** `test_worker_keeps_event_loop_live_rejects_overlap_and_defers_close`, `test_failure_preserves_last_snapshot_and_emits_no_action`.

### Save failure during autonomous tick
- **Observable symptom:** A life transaction fails while saving and Moss continues displaying the previous confirmed state.
- **Likely causes:** Filesystem permissions, locked state file, storage error, or atomic-save failure.
- **First diagnostics:** Inspect `bridge.error`, state-file accessibility, the confirmed snapshot identity, and persisted bytes.
- **Propagation risk:** Publishing the failed candidate state would make UI state disagree with disk authority.
- **Safe recovery:** Retain the confirmed snapshot and schedule one fresh normal steady interval after the failed worker completes.
- **Do not:** Do not publish the failed snapshot, mutate the state file manually, or rapid-retry.
- **Related tests:** `test_failed_autonomous_tick_preserves_snapshot_and_reschedules_normally`, `test_failure_preserves_last_snapshot_and_emits_no_action`.

### Manual Check in invalidates timer
- **Observable symptom:** The user chooses Check in while an autonomous wake or steady timer is pending.
- **Likely causes:** Normal manual interaction during an autonomous session.
- **First diagnostics:** Inspect timer activity immediately before and after `requestTick()`, plus steady cadence calls after completion.
- **Propagation risk:** Leaving the old timer alive could create a second tick too soon after the manual transaction.
- **Safe recovery:** Stop the pending timer before starting the immediate manual tick, then schedule a fresh steady interval only after completion.
- **Do not:** Do not preserve the old deadline, queue the manual tick, or schedule the steady interval before persistence completes.
- **Related tests:** `test_manual_check_in_cancels_pending_wake_and_resets_steady_schedule`.

### Suspend or resume without catch-up
- **Observable symptom:** The operating system pauses the application or machine and the habitat resumes after one or more nominal intervals elapsed.
- **Likely causes:** Sleep, hibernation, process suspension, or delayed event-loop execution.
- **First diagnostics:** Inspect persisted `last_tick`, current bridge readiness, and whether one normal timer event resumes.
- **Propagation risk:** Replaying nominal intervals could create burst transactions and multiply model/Git work.
- **Safe recovery:** Resume with the normal single-timer model; elapsed organism physics is calculated inside the next real authoritative tick.
- **Do not:** Do not reconstruct missed scheduler deadlines or issue catch-up ticks.
- **Related tests:** Lifecycle cadence and bridge scheduling tests; elapsed-time behavior remains owned by physics/tick tests.

### Multiple Moss processes
- **Observable symptom:** Two habitat processes are pointed at the same Moss home at the same time.
- **Likely causes:** The application is launched twice against one repository.
- **First diagnostics:** Check running Moss processes, repository/state paths, and state-file write activity.
- **Propagation risk:** Independent process-local locks cannot coordinate two writers to the same state file.
- **Safe recovery:** Maintain the existing one-process-per-home operating rule and close the duplicate process.
- **Do not:** Do not add inter-process coordination, distributed locking, or daemon orchestration in this milestone.
- **Related tests:** Runtime locking and persistence tests cover one-process transaction integrity; multi-process coordination is explicitly outside MOSS-LIFECYCLE-01.
