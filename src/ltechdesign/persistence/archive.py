"""Bounded ZIP codec layered on the single typed schema/domain boundary."""

import os
import stat
import struct
import zipfile
import zlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import BinaryIO

from ltechdesign.assets.validation import (
    MAX_ASSET_BYTES,
    MAX_PIXELS,
    validate_asset,
    validate_media,
)
from ltechdesign.domain.codec import MAX_JSON_BYTES, dump_project, load_project, loads
from ltechdesign.domain.errors import ModelError, fail
from ltechdesign.domain.models import Manifest, Project
from ltechdesign.domain.typing import entry_path
from ltechdesign.domain.validation import SUPPORTED_CAPABILITIES


@dataclass(frozen=True, slots=True)
class ArchiveLimits:
    entries: int = 10000
    expanded_bytes: int = 512 * 1024 * 1024
    archive_bytes: int = 528 * 1024 * 1024
    directory_bytes: int = 16 * 1024 * 1024
    asset_bytes: int = MAX_ASSET_BYTES
    raster_pixels: int = MAX_PIXELS

    def __post_init__(self) -> None:
        maxima = (
            10000,
            512 * 1024 * 1024,
            528 * 1024 * 1024,
            16 * 1024 * 1024,
            MAX_ASSET_BYTES,
            MAX_PIXELS,
        )
        for value, maximum in zip(
            (
                self.entries,
                self.expanded_bytes,
                self.archive_bytes,
                self.directory_bytes,
                self.asset_bytes,
                self.raster_pixels,
            ),
            maxima,
            strict=True,
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("Limits must be positive and cannot exceed the safe defaults")


@dataclass(frozen=True, slots=True)
class LoadedProject:
    project: Project
    blobs: Mapping[str, bytes]

    def __post_init__(self) -> None:
        object.__setattr__(self, "blobs", MappingProxyType(dict(self.blobs)))


DEFAULT_LIMITS = ArchiveLimits()


def check_cancel(cancelled: Callable[[], bool] | None) -> None:
    if cancelled is not None and cancelled():
        fail("cancelled_before_commit", code="cancelled")


def _preflight(stream: BinaryIO, limits: ArchiveLimits) -> None:
    # Bound central-directory allocation before ZipFile constructs its object list.
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    if size > limits.archive_bytes:
        fail("archive_bytes", code="limit_exceeded", maximum=limits.archive_bytes)
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    index = tail.rfind(b"PK\x05\x06")
    if index < 0 or len(tail) - index < 22:
        fail("invalid_archive")
    _, disk, central_disk, disk_count, count, central_size, offset, comment = struct.unpack_from(
        "<4s4H2IH", tail, index
    )
    if disk or central_disk or disk_count != count or index + 22 + comment != len(tail):
        fail("invalid_archive")
    if count == 65535 or central_size == 0xFFFFFFFF or offset == 0xFFFFFFFF:
        end_offset = size - len(tail) + index
        if end_offset < 20:
            fail("invalid_archive")
        stream.seek(end_offset - 20)
        signature, disk, location, disks = struct.unpack("<4sIQI", stream.read(20))
        if signature != b"PK\x06\x07" or disk or disks != 1:
            fail("invalid_archive")
        stream.seek(location)
        record = stream.read(56)
        sig, length, _, _, disk, central_disk, disk_count, count, central_size, offset = (
            struct.unpack("<4sQ2H2I4Q", record)
        )
        if sig != b"PK\x06\x06" or length != 44 or disk or central_disk or disk_count != count:
            fail("invalid_archive")
    if count > limits.entries or central_size > limits.directory_bytes:
        fail("archive_directory", code="limit_exceeded")
    if offset + central_size > size:
        fail("invalid_archive")
    # Count actual central records, not only untrusted EOCD count.
    stream.seek(offset)
    remaining, actual = central_size, 0
    while remaining:
        header = stream.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            fail("invalid_archive")
        name, extra, note = struct.unpack_from("<3H", header, 28)
        consumed = 46 + name + extra + note
        if consumed > remaining:
            fail("invalid_archive")
        stream.seek(consumed - 46, os.SEEK_CUR)
        remaining -= consumed
        actual += 1
        if actual > limits.entries:
            fail("archive_entries", code="limit_exceeded")
    if actual != count:
        fail("invalid_archive")
    stream.seek(0)


def read_archive(
    stream: BinaryIO,
    *,
    limits: ArchiveLimits = DEFAULT_LIMITS,
    cancelled: Callable[[], bool] | None = None,
) -> LoadedProject:
    """Return complete staging only. Never extract paths or alter a live session."""
    try:
        _preflight(stream, limits)
        with zipfile.ZipFile(stream) as archive:
            infos = archive.infolist()
            names: set[str] = set()
            directories: list[str] = []
            files: dict[str, zipfile.ZipInfo] = {}
            total = 0
            for info in infos:
                check_cancel(cancelled)
                name = info.orig_filename
                path = name[:-1] if info.is_dir() else name
                entry_path(path, "$.archive")
                if path.casefold() in names:
                    fail("duplicate_entry", member=name)
                names.add(path.casefold())
                kind = stat.S_IFMT(info.external_attr >> 16)
                if (
                    kind not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or (kind == stat.S_IFDIR) != info.is_dir()
                    and kind != 0
                    or info.flag_bits & 1
                    or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                ):
                    fail("unsupported_zip_member", member=name)
                total += info.file_size
                if total > limits.expanded_bytes:
                    fail("archive_expanded_bytes", code="limit_exceeded")
                if info.is_dir():
                    if info.file_size:
                        fail("invalid_directory")
                    directories.append(name)
                else:
                    files[name] = info
            if "manifest.json" not in files:
                fail("missing_entry", member="manifest.json")

            def read(info: zipfile.ZipInfo) -> bytes:
                maximum = limits.expanded_bytes
                if info.filename.endswith(".json"):
                    maximum = min(maximum, MAX_JSON_BYTES)
                if info.filename.startswith("assets/data/"):
                    maximum = min(maximum, limits.asset_bytes)
                if info.file_size > maximum:
                    fail("member_bytes", code="limit_exceeded", member=info.filename)
                result = bytearray()
                with archive.open(info) as member:
                    while chunk := member.read(min(65536, maximum - len(result) + 1)):
                        check_cancel(cancelled)
                        result.extend(chunk)
                        if len(result) > maximum:
                            fail("member_bytes", code="limit_exceeded")
                if len(result) != info.file_size:
                    fail("integrity_mismatch", member=info.filename)
                return bytes(result)

            manifest_bytes = read(files["manifest.json"])
            manifest = loads(Manifest, manifest_bytes)
            if set(manifest.required_capabilities) - SUPPORTED_CAPABILITIES:
                fail("unsupported_capability", code="unsupported_capability")
            inventory = {e.path: e for e in manifest.files}
            if set(files) != set(inventory) | {"manifest.json"}:
                fail("inventory_mismatch")
            for directory in directories:
                if not any(path.startswith(directory) for path in inventory):
                    fail("undeclared_directory")
            for path, entry in inventory.items():
                if files[path].file_size != entry.byte_length:
                    fail("integrity_mismatch", member=path)
            payloads = {"manifest.json": manifest_bytes}
            payloads.update((path, read(files[path])) for path in inventory)
        project = load_project(payloads)
        validated: set[str] = set()
        for asset in project.assets.assets:
            check_cancel(cancelled)
            if asset.path not in validated:
                validate_asset(asset, payloads[asset.path], max_pixels=limits.raster_pixels)
                validated.add(asset.path)
        for path, payload in project.opaque_files.items():
            if path.startswith("thumbnails/"):
                validate_media(payload, "image/png", max_pixels=min(limits.raster_pixels, 4194304))
        check_cancel(cancelled)
        return LoadedProject(project, {path: payloads[path] for path in validated})
    except ModelError:
        raise
    except (
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        EOFError,
        struct.error,
        zlib.error,
        UnicodeError,
        NotImplementedError,
        RuntimeError,
    ) as error:
        raise ModelError("invalid_archive") from error
    except OSError as error:
        raise ModelError("archive_read_failed", code="io_error") from error


def write_archive(
    stream: BinaryIO,
    project: Project,
    blobs: Mapping[str, bytes],
    *,
    limits: ArchiveLimits = DEFAULT_LIMITS,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    """Write staging only; the service validates it again before atomic replacement."""
    payloads = dump_project(project, blobs)
    if len(payloads) > limits.entries or sum(map(len, payloads.values())) > limits.expanded_bytes:
        fail("archive_limit", code="limit_exceeded")
    try:
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, payload in sorted(payloads.items()):
                check_cancel(cancelled)
                if path.startswith("assets/data/") and len(payload) > limits.asset_bytes:
                    fail("asset_bytes", code="limit_exceeded")
                info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                archive.writestr(info, payload)
        if stream.tell() > limits.archive_bytes:
            fail("archive_bytes", code="limit_exceeded")
    except OSError as error:
        raise ModelError("archive_write_failed", code="io_error") from error
