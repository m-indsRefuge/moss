"""Qt presentation boundary; all state I/O and ticks execute in a worker."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Property, QThread, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

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

    @Property(str, notify=stateChanged)
    def diary(self):
        return "\n\n".join(self._snapshot.diary) if self._snapshot else ""

    def __init__(self, runtime: MossRuntime):
        super().__init__()
        self._runtime = runtime
        self._snapshot: MossSnapshot | None = None
        self._job: _Operation | None = None
        self._is_tick = False
        self._closing = False
        self._error = ""

    @Property(str, constant=True)
    def repoPath(self):
        return str(self._runtime.repo)

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
        return "State saved. Ticks happen only when you ask." if self.ready else "Moss has not loaded."

    @Slot()
    def open(self):
        self._start(False)

    @Slot()
    def requestTick(self):
        if self.ready:
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
        self._error = job.error
        if job.snapshot is not None:
            self._snapshot = job.snapshot
            self.stateChanged.emit()
            if self._is_tick:
                self.tickCompleted.emit(animation_state(job.snapshot.action))
        self._job = None
        job.deleteLater()
        self.activityChanged.emit()
        if self._closing:
            self.closeReady.emit()

    @Slot()
    def requestClose(self):
        self._closing = True
        self.activityChanged.emit()
        if not self.busy:
            self.closeReady.emit()

    def finish_shutdown(self):
        # Defensive cleanup if the event loop exits outside the window-close
        # path. Normal close stays in the event loop until finished arrives.
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
