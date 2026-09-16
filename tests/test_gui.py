"""Qt event-loop and real-core integration. No screenshot comparison tests."""
import os
import subprocess
from threading import Event, get_ident

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QEventLoop, QMetaObject, QObject, QPointF, QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlExpression
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QSignalSpy, QTest

from moss.brain import LLMBrain, ReflexBrain
from moss.clock import RealClock, SimClock
from moss.gui import MossBridge, animation_state, create_engine
from moss.runtime import MossRuntime
from moss.senses import FixtureSenses
from moss.state import load, new_state, save


@pytest.fixture(scope="module")
def app():
    application = QGuiApplication.instance() or QGuiApplication(["moss tests"])
    application.setQuitOnLastWindowClosed(False)
    return application


def until(predicate, timeout=5000):
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: loop.quit() if predicate() else None)
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    timer.start()
    deadline.start(timeout)
    if not predicate():
        loop.exec()
    timer.stop()
    deadline.stop()
    assert predicate(), "Qt operation did not finish before the test deadline"


@pytest.mark.parametrize("action", ["idle", "eat", "sleep", "play", "sulk", "unknown"])
def test_action_mapping(action):
    assert animation_state(action) == (action if action != "unknown" else "idle")


def test_worker_keeps_event_loop_live_rejects_overlap_and_defers_close(app, tmp_path):
    entered, release = Event(), Event()
    worker_threads = []
    class SlowTransport:
        def complete(self, prompt):
            worker_threads.append(get_ident())
            entered.set()
            assert release.wait(5)
            raise RuntimeError("unavailable")
    runtime = MossRuntime(tmp_path, clock=SimClock(), senses=FixtureSenses([]),
                          brain=LLMBrain(SlowTransport()))
    cadence = ScriptedCadence(wake_ms=10_000, steady_ms=10_000)
    bridge = MossBridge(runtime, cadence=cadence)
    changes, actions, closed = QSignalSpy(bridge.stateChanged), QSignalSpy(bridge.tickCompleted), QSignalSpy(bridge.closeReady)
    observed_disk = []
    bridge.stateChanged.connect(lambda: observed_disk.append(load(runtime.state_path)))
    bridge.open()
    until(lambda: not bridge.busy)
    assert bridge.ready and bridge.hunger == 0.35 and bridge.energy == 0.9
    assert changes.count() == 1 and not observed_disk[0]["diary"]
    bridge.requestTick()
    try:
        until(entered.is_set)
        bridge.requestTick()
        bridge.open()
        assert bridge.busy and changes.count() == 1 and actions.count() == 0
        # This callback can run only if the UI event loop is still processing.
        heartbeat = []
        QTimer.singleShot(0, lambda: heartbeat.append(True))
        until(lambda: bool(heartbeat))
        bridge.requestClose()
        assert bridge.closing and closed.count() == 0
        assert not bridge._life_timer.isActive()
    finally:
        release.set()
        until(lambda: not bridge.busy)
        bridge.finish_shutdown()
    assert closed.count() == 1 and changes.count() == 2 and actions.count() == 1
    assert cadence.steady_calls == 0
    assert all(thread != get_ident() for thread in worker_threads)
    assert bridge.brainStatus == "Reflex fallback"
    assert bridge.hasTick and bridge.usedFallback and bridge.decisionAttempts == 2
    assert len(observed_disk[-1]["diary"]) == 1
    assert bridge.diary == observed_disk[-1]["diary"][0]
    assert bridge.action == actions.at(0)[0] == "play"
    bridge.requestTick()
    assert not bridge.busy  # shutdown cannot enqueue more work


def test_failure_preserves_last_snapshot_and_emits_no_action(app, tmp_path, monkeypatch):
    runtime = MossRuntime(tmp_path, clock=SimClock(), senses=FixtureSenses([]))
    bridge = MossBridge(runtime)
    bridge.open()
    until(lambda: not bridge.busy)
    before = runtime.state_path.read_bytes()
    changed, actions = QSignalSpy(bridge.stateChanged), QSignalSpy(bridge.tickCompleted)
    def failed_save(*args):
        raise OSError("private file content should not be exposed")
    with monkeypatch.context() as patch:
        patch.setattr("moss.runtime.save", failed_save)
        bridge.requestTick()
        until(lambda: not bridge.busy)
    assert "OSError" in bridge.error and "private" not in bridge.error
    assert not bridge.diary and bridge.action == "idle"
    assert not bridge.hasTick and bridge.decisionAttempts == 0
    assert bridge.commitsEaten == 0 and bridge.lastCommitAt == ""
    assert bridge.activity == "Showing the last confirmed state."
    assert changed.count() == actions.count() == 0
    assert runtime.state_path.read_bytes() == before
    bridge.requestTick()
    until(lambda: not bridge.busy)
    assert bridge.error == "" and actions.count() == 1


def test_corrupt_state_does_not_show_fake_creature(app, tmp_path):
    path = tmp_path / "moss.state.json"
    path.write_text('{"v":1}', encoding="utf-8")
    bridge = MossBridge(MossRuntime(tmp_path))
    bridge.open()
    until(lambda: not bridge.busy)
    assert not bridge.ready and "StateError" in bridge.error
    bridge.requestTick()
    assert not bridge.busy and path.read_text(encoding="utf-8") == '{"v":1}'


def test_qml_loads_real_snapshot_and_replays_each_action(app, tmp_path):
    bridge = MossBridge(MossRuntime(tmp_path, clock=SimClock(), senses=FixtureSenses([])))
    engine = create_engine(bridge)
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(str(e) for e in errors))
    window = engine.rootObjects()[0]
    try:
        bridge.open()
        until(lambda: not bridge.busy)
        creature = window.findChild(QObject, "creature")
        assert creature is not None and creature.property("visible")
        assert creature.property("state") == "idle"
        assert creature.property("mood") == "content"
        for action in ("eat", "sleep", "play", "sulk", "sulk"):
            bridge.tickCompleted.emit(action)
            assert creature.property("state") == action
        until(lambda: creature.property("state") == "idle", timeout=5500)
        assert not warnings
    finally:
        window.hide()
        engine.deleteLater()
        app.processEvents()


def test_real_git_tick_runs_in_worker_and_persists_meal(app, tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    git("init", "-q")
    git("-c", "user.name=Moss Test", "-c", "user.email=moss@example.invalid",
        "commit", "--allow-empty", "--no-gpg-sign", "-qm", "test meal")
    # Seed through core persistence in this disposable test repository only.
    save(tmp_path / "moss.state.json", new_state("Moss", SimClock().now()))
    bridge = MossBridge(MossRuntime(tmp_path, clock=RealClock()))
    bridge.open()
    until(lambda: not bridge.busy)
    bridge.requestTick()
    until(lambda: not bridge.busy)
    assert not bridge.error
    assert bridge.action == "eat" and bridge.repoStatus == "Git history read"
    state = load(tmp_path / "moss.state.json")
    assert state["stats"]["commits_eaten"] == 1 and state["bowl"]["commits"] == 0
    assert bridge.lastTick == state["last_tick"]


def test_habitat_button_publishes_saved_outcome_and_disclosures_do_not_tick(app, tmp_path, monkeypatch):
    class Personality:
        calls = 0

        def complete(self, prompt):
            self.calls += 1
            return ("THOUGHT: A little meal.\nACTION: eat\nMOOD: content\n"
                    "DIARY: <b>I ate two commits.</b>\nWISH: more leaves")

    brain = Personality()
    runtime = MossRuntime(tmp_path, clock=SimClock(),
                          senses=FixtureSenses([{"new_commits": 2}]), brain=LLMBrain(brain))
    seed = new_state("Moss", runtime.clock.now())
    seed["diary"] = ["My older note."]
    save(runtime.state_path, seed)
    bridge = MossBridge(runtime)
    engine = create_engine(bridge)
    window = engine.rootObjects()[0]
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(str(e) for e in errors))
    try:
        bridge.open()
        until(lambda: not bridge.busy)
        assert not bridge.hasTick and not brain.calls
        button = window.findChild(QQuickItem, "tickButton")
        assert button.property("text") == "Check in"
        assert bridge.activity == "Moss is awake and watching the repository."
        window.resize(540, 700)
        QTest.qWait(100)
        button = window.findChild(QQuickItem, "tickButton")
        point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
        assert 0 < point.x() < window.width() and 0 < point.y() < window.height()
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
        until(lambda: bridge.hasTick and not bridge.busy)
        saved = load(runtime.state_path)
        assert brain.calls == 1 and bridge.decisionAttempts == 1 and not bridge.usedFallback
        assert bridge.commitsArrived == bridge.commitsEatenThisTick == bridge.commitsEaten == 2
        assert bridge.commitsEaten == saved["stats"]["commits_eaten"]
        latest = window.findChild(QObject, "latestDiary")
        assert latest.property("text") == saved["diary"][-1] == "<b>I ate two commits.</b>"
        plain = QQmlExpression(engine.contextForObject(latest), latest, "textFormat === 0")
        assert plain.evaluate()[0] is True  # Model markup stays literal.
        assert window.findChild(QObject, "mealSummary").property("text") == "Last tick · 2 arrived in the bowl · 2 eaten"
        assert window.findChild(QObject, "bowlLabel").property("text") == "0 commits"
        assert window.findChild(QObject, "thoughtLabel").property("text") == "A little meal."
        detached = bridge.diaryEntries
        detached.clear()
        assert bridge.diaryEntries == list(reversed(saved["diary"]))
        before = runtime.state_path.read_bytes()
        # Disclosure signals exercise their QML handlers; they are presentation-only.
        for name in ("historyButton", "detailsButton"):
            assert QMetaObject.invokeMethod(window.findChild(QObject, name), "clicked", Qt.DirectConnection)
        assert window.property("historyOpen") and window.property("detailsOpen")
        assert window.findChild(QObject, "habitatDetails").property("visible")
        until(lambda: window.findChild(QObject, "creature").property("state") == "idle", timeout=5500)
        assert brain.calls == 1 and runtime.state_path.read_bytes() == before

        # A later failed save retains the completed tick's entire visible projection.
        confirmed = bridge._snapshot
        def failed_save(*args):
            raise OSError("blocked")
        monkeypatch.setattr("moss.runtime.save", failed_save)
        bridge.requestTick()
        until(lambda: not bridge.busy)
        assert bridge.error and bridge._snapshot is confirmed
        assert latest.property("text") == saved["diary"][-1]
        assert bridge.commitsArrived == 2 and runtime.state_path.read_bytes() == before
        assert not warnings
    finally:
        bridge.finish_shutdown()
        window.hide()
        engine.deleteLater()
        app.processEvents()


def test_desktop_reflows_and_keeps_history_and_tick_accessible(app, tmp_path):
    """Region relationships and reachable content, never pixel comparisons."""
    runtime = MossRuntime(tmp_path, clock=SimClock(), senses=FixtureSenses([]))
    seed = new_state("Moss", runtime.clock.now())
    seed["diary"] = [f"Earlier note {i}. " + "A quiet corner of the repository. " * 5 for i in range(12)]
    save(runtime.state_path, seed)
    before = runtime.state_path.read_bytes()
    bridge = MossBridge(runtime)
    engine = create_engine(bridge)
    window = engine.rootObjects()[0]
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(str(e) for e in errors))
    try:
        bridge.open()
        until(lambda: not bridge.busy)
        creature = window.findChild(QQuickItem, "creature")
        garden = window.findChild(QQuickItem, "gardenRegion")
        notes = window.findChild(QQuickItem, "notesRegion")
        page = window.findChild(QQuickItem, "habitatScroll")
        for width, height in ((1020, 800), (1020, 756), (1020, 700), (1280, 960), (540, 700), (899, 760), (900, 760)):
            window.resize(width, height)
            QTest.qWait(80)
            assert window.findChild(QQuickItem, "creature") is creature
            if window.property("wide"):
                assert notes.x() >= garden.x() + garden.width()
                assert notes.y() == garden.y()
            else:
                assert notes.y() >= garden.y() + garden.height()
                assert notes.width() <= page.width()
            button = window.findChild(QQuickItem, "tickButton")
            pos = button.mapToScene(QPointF(0, 0))
            assert pos.x() >= 0 and pos.y() >= 0
            assert pos.x() + button.width() <= window.width()
            assert pos.y() + button.height() <= window.height()
            if window.property("wide"):
                vitals = window.findChild(QQuickItem, "vitals")
                bottom = vitals.mapToItem(page, QPointF(0, vitals.height()))
                assert bottom.y() <= page.height() + 1

        window.resize(540, 700)
        for name in ("historyButton", "detailsButton"):
            QMetaObject.invokeMethod(window.findChild(QObject, name), "clicked", Qt.DirectConnection)
        QTest.qWait(100)
        page.setProperty("contentY", page.property("contentHeight") - page.height())
        journal = window.findChild(QQuickItem, "journalScroll")
        flick = journal.property("contentItem")
        assert flick.property("contentHeight") > flick.property("height")
        flick.setProperty("contentY", flick.property("contentHeight") - flick.property("height"))
        QTest.qWait(80)
        assert flick.property("atYEnd")
        assert window.findChild(QObject, "diaryHistory").property("visible")
        assert not bridge.hasTick and runtime.state_path.read_bytes() == before
        assert not warnings
    finally:
        bridge.finish_shutdown()
        window.hide()
        engine.deleteLater()
        app.processEvents()


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


def test_successful_open_schedules_one_wake_tick_then_one_steady_timer(app, tmp_path):
    cadence = ScriptedCadence(wake_ms=20, steady_ms=10_000)
    runtime = MossRuntime(
        tmp_path,
        clock=SimClock(),
        senses=FixtureSenses([]),
    )
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



def test_manual_check_in_cancels_pending_wake_and_resets_steady_schedule(app, tmp_path):
    cadence = ScriptedCadence(wake_ms=10_000, steady_ms=10_000)
    bridge = MossBridge(
        MossRuntime(
            tmp_path,
            clock=SimClock(),
            senses=FixtureSenses([]),
        ),
        cadence=cadence,
    )
    actions = QSignalSpy(bridge.tickCompleted)

    bridge.open()
    until(lambda: bridge.ready and not bridge.busy)

    assert bridge._life_timer.isActive()
    assert cadence.wake_calls == 1

    bridge.requestTick()

    # Manual Check in invalidates the pending autonomous wake immediately.
    assert not bridge._life_timer.isActive()

    until(lambda: actions.count() == 1 and not bridge.busy)

    assert cadence.steady_calls == 1
    assert bridge._life_timer.isActive()

    bridge.requestClose()
    assert not bridge._life_timer.isActive()
    bridge.finish_shutdown()


def test_failed_autonomous_tick_preserves_snapshot_and_reschedules_normally(
    app, tmp_path, monkeypatch
):
    cadence = ScriptedCadence(wake_ms=10_000, steady_ms=10_000)
    runtime = MossRuntime(
        tmp_path,
        clock=SimClock(),
        senses=FixtureSenses([]),
    )
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

    # Hard failure does not rapid-retry. It returns to the normal cadence.
    assert cadence.steady_calls == 1
    assert bridge._life_timer.isActive()

    bridge.requestClose()
    assert not bridge._life_timer.isActive()
    bridge.finish_shutdown()
