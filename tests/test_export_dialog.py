import json
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import test_drawing_tools as drawing_tools
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from ltechdesign.commands import Create, Delete, Move
from ltechdesign.domain import create_node
from ltechdesign.domain.models import Fill, Style
from ltechdesign.exports import ExportService
from ltechdesign.exports.contracts import TERMINAL
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop
editor = drawing_tools.editor


@pytest.mark.parametrize("format_index", [0, 1, 2])
def test_ui_service_identical_snapshot_pixels_without_editor_overlays(
    editor: tuple[StudioWindow, Tab, EditorCanvas], qtbot: QtBot, tmp_path: Path, format_index: int
) -> None:
    window, tab, view = editor
    page = tab.dispatcher.snapshot.project.document.pages[0].id
    board = create_node("artboard", page, width=240, height=160)
    leaf = replace(
        create_node("rectangle", page, width=90, height=60),
        parent_id=board.id,
        x=20,
        y=15,
        style=Style(fill=Fill(color="#1050A080"), radius=(12, 12, 12, 12)),
    )
    assert window.execute(tab, (Create(node=board), Create(node=leaf)))
    view.set_selection((leaf.id,))
    # A renderer preview is deliberately different from persisted content.
    resources = view.adapter.resources
    assert resources
    view.adapter.resources = replace(resources, previews={leaf.id: replace(leaf, x=140)})
    snapshot = tab.dispatcher.snapshot
    history = tab.dispatcher.undo_history
    window.menu_actions["export"].trigger()
    dialog = window.exports.dialogs[-1]
    ui, api = tmp_path / "ui", tmp_path / "api"
    ui.mkdir()
    api.mkdir()
    dialog.folder.setText(str(ui))
    dialog.target.setCurrentIndex(1)
    dialog.pattern.setText("same")
    dialog.format.setCurrentIndex(format_index)
    dialog.lossless.setChecked(format_index == 2)
    dialog.scale.setCurrentIndex(3)
    dialog.pixel_width.setValue(300)
    dialog.pixel_height.setValue(200)
    dialog.dpi.setValue(240)
    options = dialog.options()
    dialog.export_button.click()
    assert dialog.job_id
    qtbot.waitUntil(
        lambda: window.exports.service.get_job_status(dialog.job_id or "").state in TERMINAL,
        timeout=25000,
    )
    ui_status = window.exports.service.get_job_status(dialog.job_id)
    assert ui_status.state == "succeeded", ui_status
    service = ExportService(allowed_roots=(api,))
    try:
        direct = service.submit(
            snapshot,
            tab.store,
            replace(options, folder=str(api)),
            expected_revision=snapshot.revision,
            request_id="direct",
        )
        qtbot.waitUntil(lambda: service.get_job_status(direct.id).state in TERMINAL, timeout=25000)
        direct_status = service.get_job_status(direct.id)
        assert direct_status.state == "succeeded", direct_status
        qtbot.waitUntil(lambda: dialog.progress.value() == 1000)
        assert ui_status.committed[0].read_bytes() == direct_status.committed[0].read_bytes()
        assert QImage(str(ui_status.committed[0])).size().toTuple() == (300, 200)
        assert tab.dispatcher.snapshot is snapshot and tab.dispatcher.undo_history == history
        assert "succeeded" in dialog.report.toPlainText()
        assert not dialog.cancel_button.isEnabled()
    finally:
        service.shutdown()


def test_export_is_nonblocking_and_close_cancels_drains_its_snapshot(
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    qtbot: QtBot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, _ = editor
    board = create_node("artboard", tab.dispatcher.snapshot.project.document.pages[0].id)
    assert window.execute(tab, (Create(node=board),))
    window.exports.open()
    dialog = window.exports.dialogs[-1]
    dialog.folder.setText(str(tmp_path))
    entered, release = threading.Event(), threading.Event()
    original = window.exports.service._run

    def paused(*args: Any, **kwargs: Any) -> None:
        entered.set()
        assert release.wait(10)
        original(*args, **kwargs)

    monkeypatch.setattr(window.exports.service, "_run", paused)
    ticks: list[bool] = []
    timer = QTimer(window)
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start(10)
    dialog.start()
    qtbot.waitUntil(entered.is_set)
    qtbot.waitUntil(lambda: len(ticks) >= 3)
    assert dialog.job_id
    job_id = dialog.job_id
    before = tab.dispatcher.snapshot.revision
    assert window.execute(tab, (Move(node_id=board.id, dx=10, dy=0),))
    window.close_tab(0)
    assert (
        tab in window.documents and window.exports.service.get_job_status(job_id).cancel_requested
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    release.set()
    qtbot.waitUntil(lambda: tab not in window.documents, timeout=15000)
    status = window.exports.service.get_job_status(job_id)
    assert status.state == "cancelled" and status.source_revision == before
    assert not list(tmp_path.glob("*.png"))
    assert not window.exports.dialogs


def test_expired_job_status_does_not_delete_user_output_or_crash_dialog(
    editor: tuple[StudioWindow, Tab, EditorCanvas], qtbot: QtBot, tmp_path: Path
) -> None:
    window, tab, _ = editor
    board = create_node("artboard", tab.dispatcher.snapshot.project.document.pages[0].id)
    assert window.execute(tab, (Create(node=board),))
    window.exports.open()
    dialog = window.exports.dialogs[-1]
    dialog.folder.setText(str(tmp_path))
    dialog.start()
    assert dialog.job_id
    job_id = dialog.job_id
    qtbot.waitUntil(
        lambda: window.exports.service.get_job_status(job_id).state in TERMINAL, timeout=20000
    )
    status = window.exports.service.get_job_status(job_id)
    window.exports.service._jobs[job_id].finished = 0
    window.exports.poll()
    assert dialog.job_id is None and dialog.export_button.isEnabled()
    assert status.committed[0].exists()


def test_actual_16mp_export_cancellation_keeps_gui_heartbeat(
    editor: tuple[StudioWindow, Tab, EditorCanvas], qtbot: QtBot, tmp_path: Path
) -> None:
    window, tab, _ = editor
    board = create_node("artboard", tab.dispatcher.snapshot.project.document.pages[0].id)
    assert window.execute(tab, (Create(node=board),))
    window.exports.open()
    dialog = window.exports.dialogs[-1]
    dialog.folder.setText(str(tmp_path))
    dialog.scale.setCurrentIndex(3)
    dialog.pixel_width.setValue(4096)
    dialog.pixel_height.setValue(4096)
    ticks: list[float] = []
    timer = QTimer(window)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start(10)
    started = time.monotonic()
    dialog.start()
    assert dialog.job_id
    job_id = dialog.job_id
    service = window.exports.service
    qtbot.waitUntil(lambda: service.get_job_status(job_id).phase == "encoding", timeout=20000)
    cancellation = time.monotonic()
    dialog.cancel()
    qtbot.waitUntil(lambda: service.get_job_status(job_id).state in TERMINAL, timeout=10000)
    result = service.get_job_status(job_id)
    timer.stop()
    assert len(ticks) >= 3
    assert result.state == "cancelled" and not result.committed, result
    assert not list(tmp_path.glob("*.tmp")) and not list(tmp_path.glob("*.png"))
    gaps = [b - a for a, b in zip(ticks, ticks[1:], strict=False)]
    assert max(gaps, default=0) < 0.5
    evidence = {
        "render_pixels": 4096 * 4096,
        "state": result.state,
        "duration_ms": (time.monotonic() - started) * 1000,
        "cancel_ms": (time.monotonic() - cancellation) * 1000,
        "gui_heartbeats": len(ticks),
        "max_gap_ms": max(gaps, default=0) * 1000,
    }
    path = Path(__file__).resolve().parents[1] / "artifacts/segment15-large-cancel.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def test_dialog_artboard_choices_follow_live_document_without_losing_options(
    editor: tuple[StudioWindow, Tab, EditorCanvas], qtbot: QtBot
) -> None:
    window, tab, _ = editor
    page = tab.dispatcher.snapshot.project.document.pages[0].id
    first = create_node("artboard", page)
    assert window.execute(tab, (Create(node=first),))
    window.exports.open()
    dialog = window.exports.dialogs[-1]
    dialog.dpi.setValue(300)
    second = create_node("artboard", page, width=300, height=200)
    assert window.execute(tab, (Create(node=second),))
    qtbot.waitUntil(lambda: dialog.artboard.count() == 2)
    assert dialog.artboard.currentData() == first.id
    assert dialog.dpi.value() == 300
    dialog.artboard.setCurrentIndex(1)
    assert window.execute(tab, (Delete(node_id=second.id),))
    qtbot.waitUntil(lambda: dialog.artboard.count() == 1)
    assert dialog.artboard.currentData() == first.id
