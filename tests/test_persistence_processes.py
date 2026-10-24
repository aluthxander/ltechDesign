"""Real process boundaries: no fake lock, service, filesystem or replace adapters."""

import json
import os
import subprocess
import sys
import threading
import zipfile
from collections.abc import Iterator
from pathlib import Path
from queue import Empty, Queue
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/proyek-contoh.ltechdesign"
pytestmark = pytest.mark.core


class Worker:
    def __init__(self, directory: Path, log: list[dict[str, Any]]) -> None:
        self.log = log
        self.errors = (directory / f"child-{len(log)}.stderr").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "scripts/persistence_worker.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.errors,
            text=True,
            encoding="utf-8",
            cwd=directory,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.queue: Queue[str] = Queue()

        def reader() -> None:
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.queue.put(line)
            self.queue.put("")

        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()
        assert self.receive()["ready"]

    def receive(self) -> dict[str, Any]:
        try:
            line = self.queue.get(timeout=15)
        except Empty:
            pytest.fail(f"Child {self.process.pid} did not respond within 15 seconds")
        assert line, f"Child exited unexpectedly: {self.process.poll()}"
        result: dict[str, Any] = json.loads(line)
        self.log.append({"response": result})
        return result

    def send(self, op: str, **arguments: Any) -> None:
        message = {"op": op, **arguments}
        self.log.append({"pid": self.process.pid, "request": message})
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def call(self, op: str, **arguments: Any) -> dict[str, Any]:
        self.send(op, **arguments)
        return self.receive()

    def crash(self) -> None:
        self.process.kill()
        self.process.wait(timeout=10)
        self.log.append({"pid": self.process.pid, "killed_exit_code": self.process.returncode})

    def finish(self) -> None:
        try:
            if self.process.poll() is None:
                self.call("exit")
                assert self.process.wait(timeout=10) == 0
        finally:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=10)
            self.reader.join(timeout=2)
            for stream in (self.process.stdin, self.process.stdout):
                if stream is not None:
                    stream.close()
            self.errors.close()


@pytest.fixture
def pair(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[tuple[Worker, Worker, Path]]:
    log: list[dict[str, Any]] = []
    workers: list[Worker] = []
    try:
        workers.append(Worker(tmp_path, log))
        workers.append(Worker(tmp_path, log))
        assert workers[0].process.pid != workers[1].process.pid != os.getpid()
        path = tmp_path / "source.ltechdesign"
        path.write_bytes(FIXTURE.read_bytes())
        yield workers[0], workers[1], path
    finally:
        for worker in workers:
            worker.finish()
        output = ROOT / "artifacts/segment04a"
        output.mkdir(parents=True, exist_ok=True)
        (output / f"{request.node.name}.json").write_text(
            json.dumps(log, indent=2), encoding="utf-8"
        )


def denied(result: dict[str, Any], code: str = "file_owned") -> None:
    assert result.get("ok") is False and result.get("code") == code, result


def test_second_writer_readonly_and_close_release(pair: tuple[Worker, Worker, Path]) -> None:
    a, b, path = pair
    first = a.call("open", path=str(path))
    assert first["ok"]
    alias = str(path.parent / ".." / path.parent.name / path.name)
    if os.name == "nt":
        alias = alias.upper()
    denied(b.call("open", path=alias))
    reader = b.call("open", path=str(path), read_only=True)
    assert reader["ok"] and reader["read_only"]
    assert reader["session_id"] != first["session_id"]
    denied(b.call("save"), "read_only")
    assert b.call("close")["ok"]
    assert a.call("close")["ok"]
    assert not Path(str(path) + ".lock").exists()
    assert b.call("open", path=alias)["ok"]


def test_crash_stale_lock_and_active_owner_never_stolen(pair: tuple[Worker, Worker, Path]) -> None:
    a, b, path = pair
    assert a.call("open", path=str(path))["ok"]
    lock = Path(str(path) + ".lock")
    original = lock.read_bytes()
    # Age alone must never invalidate a long-lived owner.
    os.utime(lock, (1, 1))
    for _ in range(2):
        denied(b.call("open", path=str(path)))
    assert lock.read_bytes() == original and a.process.poll() is None
    a.crash()
    assert lock.exists() and lock.read_bytes() == original
    assert b.call("open", path=str(path))["ok"]
    assert lock.read_bytes() != original
    assert b.call("close")["ok"]
    assert not lock.exists()


@pytest.mark.parametrize("changed_bytes", [False, True])
def test_external_replace_blocks_save_and_save_as_recovers(
    pair: tuple[Worker, Worker, Path],
    changed_bytes: bool,
) -> None:
    a, b, path = pair
    assert a.call("open", path=str(path))["ok"]
    # Byte-identical replacement still changes file identity and must conflict.
    replacement = path.with_name("external.ltechdesign")
    replacement.write_bytes(FIXTURE.read_bytes())
    if changed_bytes:
        with zipfile.ZipFile(replacement, "a") as archive:
            archive.comment = b"external writer changed this container"
    assert b.call("replace_external", path=str(path), replacement=str(replacement))["ok"]
    external = path.read_bytes()
    denied(a.call("save"), "external_change_conflict")
    assert path.read_bytes() == external
    copy = path.with_name("rescued.ltechdesign")
    assert a.call("save", target=str(copy))["ok"]
    assert path.read_bytes() == external
    assert b.call("open", path=str(path))["ok"]
    denied(b.call("open", key="target", path=str(copy)))


@pytest.mark.skipif(os.name != "nt", reason="Windows read handle denies target replacement")
def test_save_as_real_io_failure_and_success_lock_lifecycle(
    pair: tuple[Worker, Worker, Path],
) -> None:
    a, b, source = pair
    opened = a.call("open", path=str(source))
    assert opened["ok"]
    target = source.with_name("target.ltechdesign")
    target.write_bytes(FIXTURE.read_bytes())
    source_bytes, target_bytes = source.read_bytes(), target.read_bytes()
    assert b.call("hold", path=str(target))["ok"]
    for blocked in (True, False):
        a.send("save", target=str(target), overwrite=True, pause=True)
        assert a.receive()["paused"]
        # Handshake pauses actual save after acquiring BOTH locks, before the first write.
        denied(b.call("open", key="probe-source", path=str(source)))
        denied(b.call("open", key="probe-target", path=str(target)))
        a.send("resume")
        result = a.receive()
        if blocked:
            denied(result, "io_error")
            assert target.read_bytes() == target_bytes and source.read_bytes() == source_bytes
            denied(b.call("open", key="probe-source", path=str(source)))
            assert b.call("open", key="target", path=str(target))["ok"]
            assert b.call("close", key="target")["ok"]
            assert b.call("release")["ok"]
            assert not list(source.parent.glob(".ltechdesign-*.tmp"))
        else:
            assert result["ok"] and result["session_id"] == opened["session_id"]
            assert source.read_bytes() == source_bytes
            assert b.call("open", key="source", path=str(source))["ok"]
            denied(b.call("open", key="target", path=str(target)))
    assert a.call("close")["ok"]
    assert b.call("open", key="target", path=str(target))["ok"]


def test_same_document_id_copies_have_independent_sessions(
    pair: tuple[Worker, Worker, Path],
) -> None:
    a, b, source = pair
    copy = source.with_name("copy.ltechdesign")
    copy.write_bytes(source.read_bytes())
    first = a.call("open", path=str(source))
    second = b.call("open", path=str(copy))
    assert first["ok"] and second["ok"]
    assert first["document_id"] == second["document_id"]
    assert first["session_id"] != second["session_id"]
    assert first["revision"] == second["revision"] == 0
    assert a.call("save")["ok"] and b.call("save")["ok"]
    assert a.call("close")["ok"]
    reopened = a.call("open", path=str(source))
    assert reopened["ok"] and reopened["session_id"] != first["session_id"]
    denied(a.call("open", key="other", path=str(copy)))


def test_hardlink_alias_writer_rejected_readonly_allowed(pair: tuple[Worker, Worker, Path]) -> None:
    a, b, source = pair
    alias = source.with_name("hardlink.ltechdesign")
    os.link(source, alias)
    denied(a.call("open", path=str(source)), "path_not_allowed")
    denied(b.call("open", path=str(alias)), "path_not_allowed")
    assert a.call("open", path=str(source), read_only=True)["ok"]
    assert b.call("open", path=str(alias), read_only=True)["ok"]
