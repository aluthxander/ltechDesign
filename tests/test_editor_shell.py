from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from ltechdesign.commands import Move
from ltechdesign.ui.window import StudioWindow

pytestmark = pytest.mark.desktop
FIXTURE = Path(__file__).resolve().parents[1] / "examples/proyek-contoh.ltechdesign"


def test_tabs_invalid_open_cancel_and_save(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = StudioWindow()
    qtbot.addWidget(window)
    window.show()
    errors: list[Exception] = []
    monkeypatch.setattr(window, "show_error", errors.append)
    paths = [tmp_path / "a.ltechdesign", tmp_path / "b.ltechdesign"]
    for path in paths:
        path.write_bytes(FIXTURE.read_bytes())
        window.open_path(str(path))
        qtbot.waitUntil(lambda: not window.busy)
    first, second = window.documents
    assert first.dispatcher.snapshot.session_id != second.dispatcher.snapshot.session_id
    assert (
        first.dispatcher.snapshot.project.document.document_id
        == second.dispatcher.snapshot.project.document.document_id
    )
    key = next(
        n.id
        for n in second.dispatcher.snapshot.project.document.nodes.values()
        if n.type == "ellipse"
    )
    window.execute(second, (Move(node_id=key, dx=3, dy=0),))
    assert second.dispatcher.dirty and not first.dispatcher.dirty
    assert not first.dispatcher.undo_history
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    window.close_tab(1)
    assert window.documents == [first, second]
    bad = tmp_path / "bad.ltechdesign"
    bad.write_bytes(b"bad")
    window.open_path(str(bad))
    qtbot.waitUntil(lambda: not window.busy)
    assert errors and window.current is second
    window.save_document()
    qtbot.waitUntil(lambda: not window.busy)
    assert not second.dispatcher.dirty
    window.reload_document()
    qtbot.waitUntil(lambda: not window.busy)
    assert window.current is not second
    while window.documents:
        window.close_tab(0)
        qtbot.waitUntil(lambda: not window.busy)
    assert window.close()


def test_save_conflict_readonly_and_failed_reload(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ltechdesign.persistence import PersistenceService

    path = tmp_path / "owned.ltechdesign"
    path.write_bytes(FIXTURE.read_bytes())
    owner = PersistenceService()
    locked = owner.open(path)
    window = StudioWindow()
    qtbot.addWidget(window)
    errors: list[Exception] = []
    monkeypatch.setattr(window, "show_error", errors.append)
    window.open_path(str(path))
    qtbot.waitUntil(lambda: not window.busy)
    assert window.current is not None and window.current.handle.read_only
    assert not window.object_name.isEnabled()
    window.close_tab(0)
    qtbot.waitUntil(lambda: not window.busy)
    owner.close(locked)
    window.open_path(str(path))
    qtbot.waitUntil(lambda: not window.busy)
    tab = window.current
    assert tab is not None
    old = tab.dispatcher.snapshot
    path.write_bytes(b"external corruption")
    window.save_document()
    qtbot.waitUntil(lambda: not window.busy)
    assert errors and path.read_bytes() == b"external corruption"
    window.reload_document()
    qtbot.waitUntil(lambda: not window.busy)
    assert window.current is tab and tab.dispatcher.snapshot is old
    window.close_tab(0)
    qtbot.waitUntil(lambda: not window.busy)
    window.close()


def test_io_does_not_block_gui_event_loop(qtbot: QtBot) -> None:
    import threading

    from PySide6.QtCore import QTimer

    window = StudioWindow()
    qtbot.addWidget(window)
    release = threading.Event()
    ticks: list[bool] = []
    timer = QTimer(window)
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start(10)
    window.job(lambda: release.wait(3), lambda result: None)
    qtbot.waitUntil(lambda: len(ticks) >= 3)
    assert window.busy
    release.set()
    qtbot.waitUntil(lambda: not window.busy)
    window.close()


def test_new_save_as_and_readonly_promotion(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtWidgets import QFileDialog, QInputDialog

    from ltechdesign.persistence import PersistenceService

    window = StudioWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("New design", True))
    window.new_document()
    qtbot.waitUntil(lambda: not window.busy)
    tab = window.current
    assert tab is not None and tab.dispatcher.dirty
    target = tmp_path / "new.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.save_document()
    qtbot.waitUntil(lambda: not window.busy)
    assert target.exists() and not tab.dispatcher.dirty
    window.close_tab(0)
    qtbot.waitUntil(lambda: not window.busy)
    owner = PersistenceService()
    held = owner.open(target)
    window.open_path(str(target))
    qtbot.waitUntil(lambda: not window.busy)
    assert window.current is not None and window.current.handle.read_only
    copy = tmp_path / "copy.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(copy), ""))
    window.save_document(as_new=True)
    qtbot.waitUntil(lambda: not window.busy)
    assert copy.exists() and not window.current.handle.read_only
    window.close_tab(0)
    qtbot.waitUntil(lambda: not window.busy)
    owner.close(held)
    window.close()
