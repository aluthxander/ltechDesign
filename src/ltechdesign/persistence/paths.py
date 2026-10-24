"""Canonical local paths, conservative QLockFile ownership and stable baselines."""

import ctypes
import hashlib
import os
import re
import socket
import stat
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from PySide6.QtCore import QLockFile, QSysInfo

from ltechdesign.domain.errors import ModelError, fail

_GUARD = threading.RLock()
_WRITERS: set[Path] = set()


def canonical_path(path: str | Path, *, writer: bool = False) -> Path:
    try:
        supplied = Path(path).absolute()
        # Reject Windows device/ADS/trailing-dot aliases rather than acquire different locks.
        if os.name == "nt":
            if str(supplied).startswith(("\\\\?\\", "\\\\.\\")):
                fail("device_path", code="path_not_allowed")
            for part in supplied.parts[1:]:
                if (
                    ":" in part
                    or part.endswith((".", " "))
                    and part not in (".", "..")
                    or re.fullmatch(
                        r"(?i:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])", part.split(".")[0]
                    )
                ):
                    fail("path_alias", code="path_not_allowed")
        if supplied.exists():
            resolved = supplied.resolve(strict=True)
            info = resolved.stat()
            if not stat.S_ISREG(info.st_mode):
                fail("not_regular_file", code="path_not_allowed")
            if writer and info.st_nlink != 1:
                fail("hardlink_writer", code="path_not_allowed")
        else:
            if supplied.is_symlink():
                fail("dangling_symlink", code="path_not_allowed")
            resolved = supplied.parent.resolve(strict=True) / supplied.name
        if writer and os.name == "nt":
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
            kernel.GetDriveTypeW.restype = ctypes.c_uint
            if str(resolved).startswith("\\\\") or kernel.GetDriveTypeW(resolved.anchor) == 4:
                fail("network_writer", code="path_not_allowed")
        return Path(os.path.normcase(resolved))
    except (OSError, ValueError) as error:
        if isinstance(error, ModelError):
            raise
        raise ModelError("canonical_path_failed", code="path_not_allowed") from error


def _alive(pid: int) -> bool | None:
    if pid <= 0:
        return None
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_uint]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            code = ctypes.c_uint()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return None
            return code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return None


class WriterLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = QLockFile(str(path) + ".lock")
        self._lock.setStaleLockTime(0)
        self._closed = False
        with _GUARD:
            if path in _WRITERS:
                fail("target_in_use", code="target_in_use")
            sidecar = Path(str(path) + ".lock")
            if sidecar.is_symlink():
                fail("unsafe_lock", code="file_owned")
            if sidecar.exists():
                pid, host, _ = self._lock.getLockInfo()
                if (
                    pid <= 0
                    or host not in (socket.gethostname(), QSysInfo.machineHostName())
                    or _alive(pid) is not False
                ):
                    fail("owner_alive_or_ambiguous", code="file_owned")
            # Qt checks the dead owner again while acquiring; never force-remove.
            if not self._lock.tryLock(0):
                fail("lock_unavailable", code="file_owned")
            _WRITERS.add(path)

    def close(self) -> None:
        with _GUARD:
            if not self._closed:
                self._lock.unlock()
                _WRITERS.discard(self.path)
                self._closed = True


@dataclass(frozen=True, slots=True)
class Fingerprint:
    device: int
    inode: int
    size: int
    modified_ns: int
    digest: str


def fingerprint_stream(stream: BinaryIO, *, maximum: int) -> Fingerprint:
    before = os.fstat(stream.fileno())
    if before.st_size > maximum:
        fail("archive_bytes", code="limit_exceeded")
    stream.seek(0)
    digest, size = hashlib.sha256(), 0
    while chunk := stream.read(65536):
        size += len(chunk)
        if size > maximum:
            fail("archive_bytes", code="limit_exceeded")
        digest.update(chunk)
    after = os.fstat(stream.fileno())

    def fields(s: os.stat_result) -> tuple[int, int, int, int, int]:
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns

    if fields(before) != fields(after) or size != before.st_size:
        fail("changed_during_read", code="external_change_conflict")
    stream.seek(0)
    return Fingerprint(before.st_dev, before.st_ino, size, before.st_mtime_ns, digest.hexdigest())


def fingerprint_path(path: Path, *, maximum: int) -> Fingerprint | None:
    try:
        with path.open("rb") as stream:
            result = fingerprint_stream(stream, maximum=maximum)
        info = path.stat()
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != (
            result.device,
            result.inode,
            result.size,
            result.modified_ns,
        ):
            fail("changed_during_read", code="external_change_conflict")
        return result
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ModelError("fingerprint_failed", code="io_error") from error
