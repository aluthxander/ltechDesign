import json
import shutil
import threading
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
from pytestqt.qtbot import QtBot

from ltechdesign.commands import Create, CreatePage, Move, SetFont
from ltechdesign.domain import create_node, create_project, semantic_content
from ltechdesign.domain.codec import json_bytes
from ltechdesign.domain.models import DocumentSession, Fill, FrameData, Page, Style
from ltechdesign.persistence import PersistenceService, read_archive
from ltechdesign.persistence.recovery import RecoveryStore
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.thumbnail import generate
from ltechdesign.ui.projects import recovery_time
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop
FIXTURE = Path(__file__).resolve().parents[1] / "examples/proyek-contoh.ltechdesign"


@pytest.fixture
def studio(qtbot: QtBot, tmp_path: Path) -> Iterator[StudioWindow]:
    window = StudioWindow(data_dir=tmp_path / "settings")
    window.projects.timer.stop()
    errors: list[Exception] = []

    def show_error(error: Exception) -> None:
        errors.append(error)

    window.show_error = show_error  # type: ignore[method-assign]
    window.show()
    yield window
    qtbot.waitUntil(lambda: not window.busy, timeout=30000)
    for tab in tuple(window.documents):
        tab.dispatcher.close()
        window.service.close(tab.handle)
    window.documents.clear()
    window.close()


def opened(window: StudioWindow, qtbot: QtBot, path: Path) -> Tab:
    path.write_bytes(FIXTURE.read_bytes())
    window.open_path(str(path))
    qtbot.waitUntil(lambda: not window.busy)
    assert window.current
    return window.current


def move(window: StudioWindow, tab: Tab) -> None:
    key = next(
        n.id for n in tab.dispatcher.snapshot.project.document.nodes.values() if n.parent_id is None
    )
    assert window.execute(tab, (Move(node_id=key, dx=2, dy=0),))


def test_duplicate_and_recent_use_live_editable_model(
    studio: StudioWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = opened(studio, qtbot, tmp_path / "original.ltechdesign")
    move(studio, source)
    snapshot = source.dispatcher.snapshot
    studio.menu_actions["duplicate"].trigger()
    qtbot.waitUntil(lambda: not studio.busy)
    clone = studio.current
    assert clone and clone is not source and clone.handle.path is None
    assert clone.dispatcher.dirty and not clone.dispatcher.undo_history
    project = clone.dispatcher.snapshot.project
    assert project.document.document_id != snapshot.project.document.document_id
    assert not project.document.nodes.keys() & snapshot.project.document.nodes.keys()
    assert [n.x for n in project.document.nodes.values()] == [
        n.x for n in snapshot.project.document.nodes.values()
    ]
    assert source.dispatcher.snapshot is snapshot
    target = tmp_path / "duplicate.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    studio.save_document()
    qtbot.waitUntil(lambda: not studio.busy, timeout=30000)
    assert target.is_file() and not clone.dispatcher.dirty
    assert studio.projects.preferences.recent[0] == str(clone.handle.path)
    studio.projects.refresh_recent()
    assert studio.projects.recent_menu.actions()[0].text() == str(clone.handle.path)
    studio.projects.recent_menu.actions()[0].trigger()
    qtbot.waitUntil(lambda: not studio.busy)
    assert studio.current is clone and len(studio.documents) == 2


def test_autosave_multitab_pins_revision_during_edit_and_close(
    studio: StudioWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    a = opened(studio, qtbot, tmp_path / "a.ltechdesign")
    b = opened(studio, qtbot, tmp_path / "b.ltechdesign")
    for tab in (a, b):
        move(studio, tab)
    a_snapshot, b_snapshot = a.dispatcher.snapshot, b.dispatcher.snapshot
    entered, release = threading.Event(), threading.Event()
    original = studio.projects.recovery.write

    def paused(*args: Any, **kwargs: Any) -> Any:
        entered.set()
        assert release.wait(10)
        return original(*args, **kwargs)

    monkeypatch.setattr(studio.projects.recovery, "write", paused)
    studio.projects.autosave()
    qtbot.waitUntil(entered.is_set)
    move(studio, a)
    studio.close_tab(0)  # active job cannot discard its captured snapshot
    assert a in studio.documents
    release.set()
    qtbot.waitUntil(lambda: not studio.busy)
    assert a.autosaved_revision == a_snapshot.revision
    assert b.autosaved_revision == b_snapshot.revision
    assert a.dispatcher.dirty and b.dispatcher.dirty
    studio.projects.recovery.release()
    scanner = RecoveryStore(studio.projects.recovery.root)
    offers = scanner.scan()
    assert len(offers) == 2
    recovered = [scanner.load(o, o.entries[0]) for o in offers]
    assert {str(x.project.document.document_id) for x in recovered} == {
        str(a_snapshot.project.document.document_id)
    }  # copied source, distinct session roots
    assert all(x.project.document == a_snapshot.project.document for x in recovered)
    for offer in offers:
        offer.release()
    # Simulate timer cadence only after the previous publication finished.
    studio.projects.autosave()
    qtbot.waitUntil(lambda: not studio.busy)
    assert a.autosaved_revision == a.dispatcher.snapshot.revision


def test_manual_save_close_does_not_drop_edit_during_io(
    studio: StudioWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab = opened(studio, qtbot, tmp_path / "source.ltechdesign")
    move(studio, tab)
    captured = tab.dispatcher.snapshot
    entered, release = threading.Event(), threading.Event()
    real_save = studio.service.save

    def paused(*args: Any, **kwargs: Any) -> Any:
        entered.set()
        assert release.wait(10)
        return real_save(*args, **kwargs)

    monkeypatch.setattr(studio.service, "save", paused)
    monkeypatch.setattr("ltechdesign.ui.window.generate_thumbnail", lambda *a: None)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Save)
    studio.close_tab(0)
    qtbot.waitUntil(entered.is_set)
    move(studio, tab)
    release.set()
    qtbot.waitUntil(lambda: not studio.busy)
    assert tab in studio.documents and tab.dispatcher.dirty
    assert not studio._exit_requested
    assert tab.handle.path
    with tab.handle.path.open("rb") as stream:
        saved = read_archive(stream)
    assert saved.project.document == captured.project.document
    assert saved.project.manifest.saved_revision == captured.revision
    studio.projects.autosave()
    qtbot.waitUntil(lambda: not studio.busy)
    assert tab.autosaved_revision == captured.revision + 1


def test_autosave_unnamed_timer_readonly_io_error_and_external_conflict(
    studio: StudioWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    errors: list[Exception] = []
    monkeypatch.setattr(studio, "show_error", errors.append)
    tab = opened(studio, qtbot, tmp_path / "external.ltechdesign")
    assert tab.handle.path
    tab.handle.path.write_bytes(b"foreign writer")
    move(studio, tab)
    studio.admit(studio.prepare_admission(studio.service.new(create_project("Unsaved"), {})))
    unnamed = studio.current
    assert unnamed
    studio.projects.timer.start(15)  # timer wiring; production preference min 10s
    qtbot.waitUntil(lambda: unnamed.autosaved_revision == 0 and tab.autosaved_revision == 1)
    studio.projects.timer.stop()
    assert unnamed.dispatcher.dirty
    assert tab.handle.path.read_bytes() == b"foreign writer"
    move(studio, tab)

    def reject(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("disk full")

    monkeypatch.setattr(studio.projects.recovery, "write", reject)
    studio.projects.autosave()
    qtbot.waitUntil(lambda: not studio.busy)
    assert tab.autosaved_revision == 1 and "Autosave gagal" in tab.status
    assert tab.dispatcher.dirty
    monkeypatch.setattr("ltechdesign.ui.window.generate_thumbnail", lambda *a: None)
    studio.tabs.setCurrentWidget(tab.widget)
    studio.save_document()
    qtbot.waitUntil(lambda: not studio.busy)
    assert errors and tab.handle.path.read_bytes() == b"foreign writer"
    assert tab.dispatcher.dirty


@pytest.mark.parametrize("decision", ["restore", "discard", "later"])
def test_startup_offers_timestamp_restore_discard_later(
    studio: StudioWindow,
    qtbot: QtBot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
) -> None:
    writer = RecoveryStore(studio.projects.recovery.root)
    old = DocumentSession(project=create_project("Recovered draft"))
    writer.write(old, {})
    writer.release()
    seen: list[str] = []

    def choose(offer: Any) -> Any:
        seen.append(recovery_time(offer.entries[0]))
        return decision, offer.entries[0]

    monkeypatch.setattr(studio.projects, "choose_recovery", choose)
    studio.projects.startup()
    qtbot.waitUntil(lambda: not studio.busy)
    assert seen and "UTC" in seen[0]
    if decision == "restore":
        tab = studio.current
        assert tab and tab.handle.path is None and tab.dispatcher.dirty
        assert tab.dispatcher.snapshot.session_id != old.session_id
        target = tmp_path / "restored.ltechdesign"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
        studio.save_document()
        qtbot.waitUntil(lambda: not studio.busy, timeout=30000)
        assert target.exists() and not tab.dispatcher.dirty
    else:
        assert not studio.documents
    offers = RecoveryStore(writer.root).scan()
    assert bool(offers) == (decision == "later")
    for offer in offers:
        offer.release()


def test_portable_multipage_artboards_missing_font_edit_save_reopen_and_thumbnail(
    studio: StudioWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = tmp_path / "asset-sources"
    sources.mkdir()
    source = opened(studio, qtbot, tmp_path / "project.ltechdesign")
    with source.store.pin(source.dispatcher.snapshot.project.assets.assets) as pin:
        for asset_path, data in pin.blobs.items():
            (sources / Path(asset_path).name).write_bytes(data)
    project = source.dispatcher.snapshot.project
    font = replace(
        project.fonts.fonts[-1],
        family="AbsentFont-Segment14-88311",
        postscript_name="OriginalPS",
        fallback_families=("Arial",),
        source="system",
        asset_id=None,
    )
    page = Page(name="Second editable page")
    board = create_node("artboard", page.id, width=600, height=400)
    assert studio.execute(source, (SetFont(font=font), CreatePage(page=page), Create(node=board)))
    studio.save_document()
    qtbot.waitUntil(lambda: not studio.busy, timeout=30000)
    expected = source.dispatcher.snapshot.project
    session_id = source.dispatcher.snapshot.session_id
    assert source.handle.path
    path = source.handle.path
    with path.open("rb") as stream:
        saved = read_archive(stream)
    assert QImage.fromData(saved.project.opaque_files["thumbnails/project.png"]).width() <= 320
    assert saved.project.manifest.saved_revision == source.dispatcher.snapshot.revision
    studio.close_tab(0)
    qtbot.waitUntil(lambda: not studio.busy)
    moved = tmp_path / "elsewhere" / "only-file.ltechdesign"
    moved.parent.mkdir()
    shutil.move(str(path), moved)
    shutil.rmtree(sources)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(moved), ""))
    studio.menu_actions["import"].trigger()
    qtbot.waitUntil(lambda: not studio.busy)
    restored = studio.current
    assert restored and restored.warning_label
    assert "tidak tersedia" in restored.warning_label.text()
    assert font.family in restored.warning_label.text()
    assert (
        next(f for f in restored.dispatcher.snapshot.project.fonts.fonts if f.id == font.id) == font
    )
    assert semantic_content(restored.dispatcher.snapshot.project) == semantic_content(expected)
    assert restored.dispatcher.snapshot.session_id != session_id
    assert restored.dispatcher.snapshot.revision == 0 and not restored.dispatcher.undo_history
    studio.activate_page(restored, page.id)
    move(studio, restored)
    edited = restored.dispatcher.snapshot.project
    studio.save_document()
    qtbot.waitUntil(lambda: not studio.busy, timeout=30000)
    studio.reload_document()
    qtbot.waitUntil(lambda: not studio.busy)
    assert studio.current
    assert semantic_content(studio.current.dispatcher.snapshot.project) == semantic_content(edited)


def test_thumbnail_uses_shared_drawing_exact_pixels(studio: StudioWindow, tmp_path: Path) -> None:
    del tmp_path
    project = create_project()
    board = create_node("artboard", project.document.pages[0].id, width=320, height=200)
    board = replace(board, data=FrameData(background="#102030FF"))
    rectangle = replace(
        create_node("rectangle", board.page_id, width=80, height=50),
        parent_id=board.id,
        x=100,
        y=60,
        rotation=24,
        opacity=0.7,
        style=Style(fill=Fill(color="#F0A020FF")),
    )
    studio.admit(studio.prepare_admission(studio.service.new(project, {})))
    tab = studio.current
    assert tab and studio.execute(tab, (Create(node=board), Create(node=rectangle)))
    project = tab.dispatcher.snapshot.project
    preview = generate(project, {})
    assert preview
    expected = render_image(project.document, (board.id,), QRectF(0, 0, 320, 200))
    actual = QImage.fromData(preview).convertToFormat(expected.format())
    assert bytes(actual.constBits()) == bytes(expected.constBits())


def test_readonly_excluded_from_autosave_duplicate_has_independent_writer(
    studio: StudioWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    path = tmp_path / "owned.ltechdesign"
    path.write_bytes(FIXTURE.read_bytes())
    owner = PersistenceService()
    held = owner.open(path)
    try:
        studio.open_path(str(path))
        qtbot.waitUntil(lambda: not studio.busy)
        tab = studio.current
        assert tab and tab.handle.read_only
        studio.projects.autosave()
        assert not studio.busy and tab.autosaved_revision == -1
        studio.projects.duplicate()
        qtbot.waitUntil(lambda: not studio.busy)
        clone = studio.current
        assert clone and clone is not tab and not clone.handle.read_only
        studio.projects.autosave()
        qtbot.waitUntil(lambda: not studio.busy)
        assert clone.autosaved_revision == 0 and tab.autosaved_revision == -1
        assert path.read_bytes() == FIXTURE.read_bytes()
    finally:
        owner.close(held)


def test_configure_autosave_persists_off_and_interval(
    studio: StudioWindow, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    for interval in (30, 0):
        monkeypatch.setattr(QInputDialog, "getInt", lambda *a, n=interval, **k: (n, True))
        studio.projects.configure()
        qtbot.waitUntil(lambda: not studio.busy)
        assert studio.projects.preferences.autosave_seconds == interval
        assert studio.projects.timer.isActive() == bool(interval)
        if interval:
            assert studio.projects.timer.interval() == interval * 1000


@pytest.mark.parametrize(
    "damage", ["hash", "missing_asset", "version", "capability", "preview_only"]
)
def test_bad_import_preserves_live_tab_and_history(
    studio: StudioWindow, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    from test_persistence import members, zip_bytes

    tab = opened(studio, qtbot, tmp_path / "good.ltechdesign")
    move(studio, tab)
    snapshot, history = tab.dispatcher.snapshot, tab.dispatcher.undo_history
    payload = members()
    manifest = json.loads(payload["manifest.json"])
    if damage == "hash":
        payload["document.json"] += b" "
    elif damage == "missing_asset":
        del payload[next(p for p in payload if p.startswith("assets/data/"))]
    elif damage == "version":
        manifest["format_version"] = "99.0"
    elif damage == "capability":
        manifest["required_capabilities"].append("unknown.required/1")
    else:
        del payload["document.json"]
    payload["manifest.json"] = json_bytes(manifest)
    path = tmp_path / "bad.ltechdesign"
    path.write_bytes(zip_bytes(payload))
    errors: list[Exception] = []
    monkeypatch.setattr(studio, "show_error", errors.append)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(path), ""))
    studio.menu_actions["import"].trigger()
    qtbot.waitUntil(lambda: not studio.busy)
    assert errors and studio.current is tab and len(studio.documents) == 1
    assert tab.dispatcher.snapshot is snapshot and tab.dispatcher.undo_history == history
    assert not Path(str(path) + ".lock").exists()
