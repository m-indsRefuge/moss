"""Qt presentation boundary; all state I/O and ticks execute in a worker."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Property, QThread, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from moss.lifecycle import LifecycleCadence
from moss.runtime import MossRuntime, MossSnapshot


def animation_state(action: str) -> str:
    return action if action in ("eat", "sleep", "play", "sulk") else "idle"


class _Operation(QThread):
    """One blocking transaction, no worker event loop or cancellation mid-save."""

    def __init__(self, operation: Callable[[], MossSnapshot], parent: QObject):
        super().__init__(parent)
        self.operation = operation
        self.snapshot: MossSnapshot | None = None
        self.error = ""

    def run(self):
        try:
            self.snapshot = self.operation()
        except Exception as exc:
            # Do not render exception values that can contain raw file/model data.
            self.error = (f"{type(exc).__name__}: operation failed. No new state is displayed. "
                          "Inspect moss.state.json and filesystem access before trying again.")


def _field(name, value_type, default, changed):
    return Property(value_type, lambda self: getattr(self._snapshot, name, default),
                    notify=changed)


class MossBridge(QObject):
    stateChanged = Signal()
    activityChanged = Signal()
    tickCompleted = Signal(str)
    closeReady = Signal()

    # Named read-only properties: no raw persistent dict crosses into QML.
    name = _field("name", str, "Moss", stateChanged)
    hunger = _field("hunger", float, 0.0, stateChanged)
    energy = _field("energy", float, 0.0, stateChanged)
    bowl = _field("bowl", int, 0, stateChanged)
    mood = _field("mood", str, "", stateChanged)
    wish = _field("wish", str, "", stateChanged)
    thought = _field("thought", str, "", stateChanged)
    action = _field("action", str, "idle", stateChanged)
    lastTick = _field("last_tick", str, "", stateChanged)
    brainStatus = _field("brain_status", str, "Not run this visit", stateChanged)
    repoStatus = _field("repo_status", str, "Not sensed this visit", stateChanged)
    commitsEaten = _field("commits_eaten", int, 0, stateChanged)
    sulks = _field("sulks", int, 0, stateChanged)
    longestNeglectDays = _field("longest_neglect_days", int, 0, stateChanged)
    hasTick = _field("has_tick", bool, False, stateChanged)
    commitsArrived = _field("commits_arrived", int, 0, stateChanged)
    commitsEatenThisTick = _field("commits_eaten_this_tick", int, 0, stateChanged)
    decisionAttempts = _field("decision_attempts", int, 0, stateChanged)
    usedFallback = _field("used_fallback", bool, False, stateChanged)
    hoursQuiet = _field("hours_quiet", float, 0.0, stateChanged)
    isNight = _field("is_night", bool, False, stateChanged)
    lastCommitAt = _field("last_commit_at", str, "", stateChanged)

    @Property(str, notify=stateChanged)
    def diary(self):
        return "\n\n".join(self._snapshot.diary) if self._snapshot else ""

    @Property("QStringList", notify=stateChanged)
    def diaryEntries(self):
        # Detached newest-first presentation; QML cannot edit the snapshot.
        return list(reversed(self._snapshot.diary)) if self._snapshot else []

    def __init__(self, runtime: MossRuntime, *, cadence=None):
        super().__init__()
        self._runtime = runtime
        self._cadence = cadence if cadence is not None else LifecycleCadence()
        self._snapshot: MossSnapshot | None = None
        self._job: _Operation | None = None
        self._is_tick = False
        self._closing = False
        self._error = ""
        self._life_timer = QTimer(self)
        self._life_timer.setSingleShot(True)
        self._life_timer.timeout.connect(self._autonomous_tick)

    @Property(str, constant=True)
    def repoPath(self):
        return str(self._runtime.repo)

    @Property(str, constant=True)
    def repoName(self):
        return self._runtime.repo.name or str(self._runtime.repo)

    @Property(str, constant=True)
    def brainLabel(self):
        return self._runtime.brain_label

    @Property(str, constant=True)
    def statePath(self):
        return str(self._runtime.state_path)

    @Property(bool, notify=activityChanged)
    def busy(self):
        return self._job is not None

    @Property(bool, notify=stateChanged)
    def ready(self):
        return self._snapshot is not None

    @Property(bool, notify=activityChanged)
    def closing(self):
        return self._closing

    @Property(str, notify=activityChanged)
    def error(self):
        return self._error

    @Property(str, notify=activityChanged)
    def activity(self):
        if self._closing and self.busy:
            return "Finishing this operation before closing…"
        if self.busy:
            return "Sensing Git and consulting the brain…" if self._is_tick else "Opening Moss’s home…"
        if self._error:
            return "Showing the last confirmed state." if self.ready else "Moss could not be opened."
        return "Moss is awake and watching the repository." if self.ready else "Moss has not loaded."

    @Slot()
    def open(self):
        if not self.busy and not self._closing:
            self._life_timer.stop()
            self._start(False)

    @Slot()
    def requestTick(self):
        if self.ready and not self.busy and not self._closing:
            self._life_timer.stop()
            self._start(True)

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

    def _start(self, is_tick):
        if self.busy or self._closing:
            return  # no accumulating clicks / queued surprise ticks
        self._error = ""
        self._is_tick = is_tick
        self._job = _Operation(self._runtime.live_tick if is_tick else self._runtime.open, self)
        self._job.finished.connect(self._completed, Qt.ConnectionType.QueuedConnection)
        self.activityChanged.emit()
        self._job.start()

    @Slot()
    def _completed(self):
        job = self._job
        was_tick = self._is_tick
        self._error = job.error
        if job.snapshot is not None:
            self._snapshot = job.snapshot
            self.stateChanged.emit()
            if was_tick:
                self.tickCompleted.emit(animation_state(job.snapshot.action))
        self._job = None
        job.deleteLater()
        self.activityChanged.emit()
        if self._closing:
            self.closeReady.emit()
        elif was_tick:
            self._schedule_steady()
        elif self.ready:
            self._schedule_wake()

    @Slot()
    def requestClose(self):
        self._life_timer.stop()
        self._closing = True
        self.activityChanged.emit()
        if not self.busy:
            self.closeReady.emit()

    def finish_shutdown(self):
        # Defensive cleanup if the event loop exits outside the window-close
        # path. Normal close stays in the event loop until finished arrives.
        self._life_timer.stop()
        if self._job is not None:
            self._job.wait()


def create_engine(bridge: MossBridge) -> QQmlApplicationEngine:
    # Native light controls can make the habitat's light labels unreadable.
    if QQuickStyle.name() != "Basic":
        QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"bridge": bridge})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("qml") / "Home.qml")))
    if not engine.rootObjects():
        raise RuntimeError("Moss QML window could not load")
    return engine


def run_home(runtime: MossRuntime) -> int:
    app = QGuiApplication(["moss home"])
    app.setApplicationName("Moss")
    bridge = MossBridge(runtime)
    engine = create_engine(bridge)
    bridge.closeReady.connect(app.quit)
    QTimer.singleShot(0, bridge.open)
    try:
        return app.exec()
    finally:
        bridge.finish_shutdown()
        del engine

