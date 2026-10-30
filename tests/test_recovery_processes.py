import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from queue import Queue
from typing import Any

import pytest

from ltechdesign.persistence import read_archive
from ltechdesign.persistence.recovery import RecoveryStore

pytestmark = pytest.mark.core
ROOT = Path(__file__).resolve().parents[1]


class EditorProcess:
    def __init__(self, root: Path) -> None:
        self.stderr = (root.parent / f"{root.name}-stderr.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "scripts/recovery_worker.py"), str(root)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
            text=True,
            encoding="utf-8",
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.queue: Queue[str] = Queue()

        def reader() -> None:
            assert self.process.stdout
            for line in self.process.stdout:
                self.queue.put(line)
            self.queue.put("")

        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()
        assert self.receive()["ready"]

    def receive(self) -> dict[str, Any]:
        line = self.queue.get(timeout=35)
        assert line, f"Editor exited: {self.process.poll()}"
        result: dict[str, Any] = json.loads(line)
        return result

    def send(self, op: str, **arguments: Any) -> None:
        assert self.process.stdin
        self.process.stdin.write(json.dumps({"op": op, **arguments}) + "\n")
        self.process.stdin.flush()

    def call(self, op: str, **arguments: Any) -> dict[str, Any]:
        self.send(op, **arguments)
        result = self.receive()
        assert result.get("ok"), result
        return result

    def kill(self) -> None:
        self.process.kill()
        self.process.wait(timeout=10)

    def close(self) -> None:
        if self.process.poll() is None:
            self.call("exit")
            assert self.process.wait(timeout=10) == 0
        self.reader.join(timeout=2)
        for stream in (self.process.stdin, self.process.stdout):
            if stream:
                stream.close()
        self.stderr.close()


@pytest.mark.parametrize("named", [False, True])
@pytest.mark.parametrize("during_write", [False, True])
def test_killed_editor_restores_last_successful_snapshot_and_saves_normal_file(
    tmp_path: Path, named: bool, during_write: bool
) -> None:
    root = tmp_path / "profile"
    first = EditorProcess(root)
    source = tmp_path / "source.ltechdesign"
    before: bytes | None = None
    try:
        if named:
            source.write_bytes((ROOT / "examples/proyek-contoh.ltechdesign").read_bytes())
            before = source.read_bytes()
            first.call("open", path=str(source))
        else:
            first.call("new")
        first.call("edit")
        saved = first.call("autosave")
        assert saved["autosaved_revision"] == saved["revision"]
        assert not RecoveryStore(root / "recovery").scan()  # actual live foreign Qt process
        first.call("edit")
        if during_write:
            first.send("pause_autosave")
            assert first.receive()["paused_before_publication"]
        first.kill()
    finally:
        first.close()
    second = EditorProcess(root)
    try:
        restored = second.call("restore")
        assert restored["content"] == saved["content"]
        assert restored["revision"] == 0 and restored["undo_count"] == 0 and restored["dirty"]
        assert restored["session_id"] != saved["session_id"]
        rescued = tmp_path / "rescued.ltechdesign"
        assert not second.call("save", path=str(rescued))["dirty"]
        if before is not None:
            assert source.read_bytes() == before
        with rescued.open("rb") as stream:
            loaded = read_archive(stream)
        assert loaded.project.document.document_id == saved["content"]["document"]["document_id"]
    finally:
        second.close()


def test_close_move_only_file_delete_asset_sources_reopen_in_fresh_offline_editor(
    tmp_path: Path,
) -> None:
    source_assets = tmp_path / "original-assets"
    source_assets.mkdir()
    project = tmp_path / "project.ltechdesign"
    fixture = ROOT / "examples/proyek-contoh.ltechdesign"
    project.write_bytes(fixture.read_bytes())
    with fixture.open("rb") as stream:
        loaded = read_archive(stream)
    for name, data in loaded.blobs.items():
        (source_assets / Path(name).name).write_bytes(data)
    first = EditorProcess(tmp_path / "profile-first")
    try:
        first.call("open", path=str(project))
        edited = first.call("edit")
        checkpoint = tmp_path / "saved.ltechdesign"
        first.call("save", path=str(checkpoint))
    finally:
        first.close()
    moved = tmp_path / "elsewhere" / "only-file.ltechdesign"
    moved.parent.mkdir()
    shutil.move(str(checkpoint), moved)
    project.unlink()
    shutil.rmtree(source_assets)
    second = EditorProcess(tmp_path / "profile-fresh-offline")
    try:
        reopened = second.call("open", path=str(moved))
        assert reopened["content"] == edited["content"]
        assert reopened["session_id"] != edited["session_id"]
        assert reopened["revision"] == 0 and reopened["undo_count"] == 0
        second.call("edit")
        again = tmp_path / "edited-again.ltechdesign"
        second.call("save", path=str(again))
        with again.open("rb") as stream:
            assert read_archive(stream).blobs == loaded.blobs
    finally:
        second.close()
