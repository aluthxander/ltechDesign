"""Segment 08 warm GUI baseline, real events/painting and separate commit timing."""

import argparse
import ctypes
import hashlib
import json
import math
import os
import platform
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QBuffer, QEvent, QIODevice, QPointF, Qt, QTimer, qVersion
from PySide6.QtGui import QGuiApplication, QImage, QMouseEvent
from PySide6.QtWidgets import QApplication

from ltechdesign.commands import Dispatcher, Request, Update
from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.models import (
    Asset,
    AssetId,
    AssetsIndex,
    Document,
    DocumentSession,
    Fill,
    InventoryEntry,
    MediaData,
    NodeId,
    Project,
    Style,
)
from ltechdesign.ui.window import StudioWindow, Tab

ROOT = Path(__file__).resolve().parents[1]


def total_ram() -> int | None:
    if sys.platform != "win32":
        return None

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong)
            for name in (
                "ullTotalPhys",
                "ullAvailPhys",
                "ullTotalPageFile",
                "ullAvailPageFile",
                "ullTotalVirtual",
                "ullAvailVirtual",
                "ullAvailExtendedVirtual",
            )
        ]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(status)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return int(status.ullTotalPhys)
    return None


def fixture(count: int) -> Project:
    project = create_project(f"Benchmark08-{count}")
    page = project.document.pages[0]
    children = []
    for i in range(count):
        n = create_node("rectangle", page.id, width=12, height=12, node_id=NodeId(f"shape-{i:04d}"))
        children.append(
            replace(
                n,
                parent_id=NodeId("board"),
                x=20 + (i % 40) * 18,
                y=20 + (i // 40) * 18,
                style=Style(fill=Fill(color="#2288CCFF")),
            )
        )
    board = replace(
        create_node("artboard", page.id, width=800, height=600, node_id=NodeId("board")),
        children=tuple(n.id for n in children),
    )
    return replace(
        project,
        manifest=replace(
            project.manifest,
            required_capabilities=project.manifest.required_capabilities + ("render.clipping/1",),
        ),
        document=Document(
            document_id=project.document.document_id,
            name=project.document.name,
            pages=(replace(page, root_ids=(board.id,)),),
            nodes={n.id: n for n in [board] + children},
        ),
    )


def stats(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)

    def percentile(p: float) -> float:
        return ordered[min(len(ordered) - 1, math.ceil(len(ordered) * p) - 1)] if ordered else 0

    return {
        "samples": len(values),
        "p95_ms": percentile(0.95),
        "p99_ms": percentile(0.99),
        "max_ms": max(values, default=0),
    }


def resident_bytes() -> int | None:
    if sys.platform != "win32":
        return None

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    get_current = ctypes.windll.kernel32.GetCurrentProcess
    get_current.restype = ctypes.c_void_p
    get_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    handle = get_current()
    if get_info(handle, ctypes.byref(counters), counters.cb):
        return int(counters.WorkingSetSize)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument(
        "--images",
        action="store_true",
        help="Replace 20 percent of shapes with shared raster/SVG assets",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/segment08-benchmark.json")
    args = parser.parse_args()
    if args.seconds < 1:
        parser.error("At least one second per phase")
    app = QApplication([])

    class BenchmarkWindow(StudioWindow):
        def __init__(self) -> None:
            self.errors: list[str] = []
            super().__init__()

        def show_error(self, error: Exception) -> None:
            self.errors.append(str(error))

    window = BenchmarkWindow()
    window.show()
    report: dict[str, Any] = {
        "scope": "warm local development host, not segment23/reference release hardware",
        "python": sys.version,
        "os": platform.platform(),
        "cpu": platform.processor(),
        "logical_processors": os.cpu_count(),
        "ram_bytes": total_ram(),
        "disk_type": "not verified; no clean reference-machine claim",
        "run_kind": "warm run; cold launch and comprehensive release benchmark remain segment23",
        "qt": qVersion(),
        "platform": QGuiApplication.platformName(),
        "screens": [
            {"name": s.name(), "dpr": s.devicePixelRatio(), "logical_dpi": s.logicalDotsPerInch()}
            for s in app.screens()
        ],
        "seconds_per_phase": args.seconds,
        "source_sha256": hashlib.sha256(
            b"".join(p.read_bytes() for p in sorted((ROOT / "src").rglob("*.py")))
        ).hexdigest(),
        "phases": [],
        "memory_rounds": [],
        "errors": window.errors,
    }
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        ) as key:
            report["cpu_model"] = winreg.QueryValueEx(key, "ProcessorNameString")[0]
    except OSError:
        report["cpu_model"] = "unavailable"
    fixtures = {n: fixture(n) for n in (100, 1000)}
    blobs: dict[str, bytes] = {}
    if args.images:
        image = QImage(96, 96, QImage.Format.Format_ARGB32)
        image.fill(0xFF2288CC)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        assert image.save(buffer, "PNG")  # type: ignore[call-overload]
        payloads = (
            bytes(buffer.data().data()),
            b'<svg width="96" height="96"><circle cx="48" cy="48" r="42" fill="#22bbcc"/></svg>',
        )
        assets = tuple(
            Asset(
                id=AssetId(f"benchmark-image-{i}"),
                path="assets/data/" + hashlib.sha256(payload).hexdigest(),
                sha256=hashlib.sha256(payload).hexdigest(),
                byte_length=len(payload),
                media_type="image/png" if i == 0 else "image/svg+xml",
            )
            for i, payload in enumerate(payloads)
        )
        blobs = {a.path: p for a, p in zip(assets, payloads, strict=True)}
        for count, project in fixtures.items():
            nodes = dict(project.document.nodes)
            for i in range(0, count, 5):
                image_key = NodeId(f"shape-{i:04d}")
                nodes[image_key] = replace(
                    nodes[image_key],
                    type="image" if i % 2 == 0 else "svg",
                    data=MediaData(asset_id=assets[i % 2].id),
                    style=Style(),
                )
            fixtures[count] = replace(
                project,
                document=replace(project.document, nodes=nodes),
                assets=AssetsIndex(assets=assets),
                manifest=replace(
                    project.manifest,
                    required_capabilities=project.manifest.required_capabilities
                    + ("assets.svg/1",),
                    files=project.manifest.files
                    + tuple(
                        InventoryEntry(
                            path=a.path,
                            media_type=a.media_type,
                            byte_length=a.byte_length,
                            sha256=a.sha256,
                        )
                        for a in assets
                    ),
                ),
            )
    report["fixture_kind"] = (
        "80 percent shapes, 10 percent raster, 10 percent SVG" if args.images else "simple shapes"
    )
    phases = [(100, "pan"), (100, "drag"), (1000, "pan_selection")]
    timer = QTimer(window)
    timer.setTimerType(Qt.TimerType.PreciseTimer)
    timer.setInterval(16)
    state: dict[str, Any] = {"index": -1, "tab": None}

    def dispose() -> None:
        for tab in window.documents:
            tab.dispatcher.close()
            window.service.close(tab.handle)
        window.documents.clear()
        while window.tabs.count():
            widget = window.tabs.widget(0)
            assert widget is not None
            window.tabs.removeTab(0)
            widget.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()

    def mouse(kind: QEvent.Type, point: QPointF, button: Qt.MouseButton) -> None:
        tab: Tab = state["tab"]
        assert tab.view
        local = QPointF(tab.view.mapFromScene(point))
        event = QMouseEvent(
            kind, local, local, button, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
        )
        QApplication.sendEvent(tab.view.viewport(), event)

    def start_phase() -> None:
        state["index"] += 1
        if state["index"] == len(phases):
            finish()
            return
        dispose()
        count, kind = phases[state["index"]]
        started = time.perf_counter()
        window.admit(window.prepare_admission(window.service.new(fixtures[count], blobs)))
        tab = window.current
        assert tab and tab.view
        state.update(
            tab=tab, count=count, kind=kind, admission_ms=(time.perf_counter() - started) * 1000
        )
        tab.view.fit_artboard()
        tab.view.viewport().repaint()
        state.update(
            start=time.perf_counter(), last=time.perf_counter(), intervals=[], costs=[], frame=0
        )
        if kind == "drag":
            tab.view.set_selection((NodeId("shape-0000"),))
            mouse(QEvent.Type.MouseButtonPress, QPointF(26, 26), Qt.MouseButton.LeftButton)
        timer.start()

    def tick() -> None:
        now = time.perf_counter()
        state["intervals"].append((now - state["last"]) * 1000)
        state["last"] = now
        if now - state["start"] >= args.seconds:
            timer.stop()
            release_ms = 0.0
            if state["kind"] == "drag":
                release_start = time.perf_counter()
                mouse(QEvent.Type.MouseButtonRelease, QPointF(46, 36), Qt.MouseButton.LeftButton)
                release_ms = (time.perf_counter() - release_start) * 1000
            tab: Tab = state["tab"]
            phase = {
                "nodes": state["count"],
                "kind": state["kind"],
                "intervals": stats(state["intervals"]),
                "callback_and_repaint": stats(state["costs"]),
                "admission_ms": state["admission_ms"],
                "resident_bytes": resident_bytes(),
                "longest_event_gap_ms": max(state["intervals"]),
                "freeze_over_16ms_ms": max(0, max(state["intervals"]) - 16),
                "release_commit_gui_ms": release_ms,
                "history_entries": len(tab.dispatcher.undo_history),
            }
            report["phases"].append(phase)
            QTimer.singleShot(0, start_phase)
            return
        tab = state["tab"]
        assert tab.view
        frame = state["frame"]
        offset = math.sin(frame / 20) * 40
        if state["kind"] == "drag":
            mouse(QEvent.Type.MouseMove, QPointF(46 + offset, 36), Qt.MouseButton.NoButton)
        else:
            tab.view.centerOn(400 + offset, 300)
            if state["kind"] == "pan_selection" and frame % 30 == 0:
                keys = tuple(
                    n.id
                    for n in tab.dispatcher.snapshot.project.document.nodes.values()
                    if n.type == "rectangle"
                )
                tab.view.set_selection(keys if frame % 60 == 0 else (keys[frame % len(keys)],))
        tab.view.viewport().repaint()
        state["costs"].append((time.perf_counter() - now) * 1000)
        state["frame"] += 1

    def finish() -> None:
        dispose()
        project = fixtures[1000]
        dispatcher = Dispatcher(DocumentSession(project=project))
        commits = []
        for i in range(3):
            snapshot = dispatcher.snapshot
            changes = tuple(
                Update(
                    node=replace(
                        snapshot.project.document.nodes[NodeId(f"shape-{n:04d}")], x=30 + i
                    )
                )
                for n in range(100)
            )
            request = Request(
                session_id=snapshot.session_id,
                expected_revision=snapshot.revision,
                request_id=str(uuid4()),
                action_name="Benchmark100",
                source="GUI",
                operations=changes,
            )
            start = time.perf_counter()
            result = dispatcher.dispatch(request, client_id="benchmark")
            commits.append((time.perf_counter() - start) * 1000)
            assert result.ok, result.error
        report["batch100_commit_only"] = stats(commits)
        dispatcher.close()
        window.admit(window.prepare_admission(window.service.new(project, blobs)))
        tab = window.current
        assert tab and tab.view
        changes = tuple(
            Update(node=replace(project.document.nodes[NodeId(f"shape-{n:04d}")], x=35))
            for n in range(100)
        )
        ui_start = time.perf_counter()
        heartbeat: list[float] = []
        QTimer.singleShot(0, lambda: heartbeat.append((time.perf_counter() - ui_start) * 1000))
        assert window.execute(tab, changes, action_name="Benchmark100 GUI")
        report["batch100_gui_command_ms"] = (time.perf_counter() - ui_start) * 1000
        tab.view.viewport().repaint()
        app.processEvents()
        report["batch100_gui_heartbeat_gap_ms"] = heartbeat[0] if heartbeat else None
        dispose()
        for _ in range(3):
            window.admit(window.prepare_admission(window.service.new(project, blobs)))
            assert window.current and window.current.view
            window.current.view.viewport().repaint()
            dispose()
            report["memory_rounds"].append(resident_bytes())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
        window.close()
        app.quit()

    timer.timeout.connect(tick)
    QTimer.singleShot(100, start_phase)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
