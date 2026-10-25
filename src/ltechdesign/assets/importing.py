"""Bounded local import staging. Cancellation never publishes document content."""

import hashlib
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ltechdesign.domain.errors import fail
from ltechdesign.domain.models import Asset, AssetId, new_id
from ltechdesign.rendering.media import MAX_PREPARED_BYTES, MediaSource, prepare_source

from .store import BlobStore
from .validation import MAX_ASSET_BYTES


@dataclass(frozen=True)
class StagedImage:
    asset: Asset
    staging_id: str
    source: MediaSource
    name: str


def check_cancel(cancelled: Callable[[], bool]) -> None:
    if cancelled():
        fail("Import cancelled", code="cancelled")


def stage_image(
    path: Path,
    store: BlobStore,
    cancelled: Callable[[], bool],
    *,
    byte_budget: int = MAX_PREPARED_BYTES,
) -> StagedImage:
    check_cancel(cancelled)
    # File descriptor size, then bounded reads: a growing/replaced source cannot bypass limits.
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            fail("image_file_required")
        if info.st_size > MAX_ASSET_BYTES:
            fail("asset_bytes", code="limit_exceeded", maximum=MAX_ASSET_BYTES)
        chunks: list[bytes] = []
        total = 0
        while True:
            check_cancel(cancelled)
            chunk = stream.read(min(1024 * 1024, MAX_ASSET_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ASSET_BYTES:
                fail("asset_bytes", code="limit_exceeded", maximum=MAX_ASSET_BYTES)
            chunks.append(chunk)
    payload = b"".join(chunks)
    media: Literal["image/png", "image/jpeg", "image/webp", "image/svg+xml"] = (
        "image/png"
        if payload.startswith(b"\x89PNG\r\n\x1a\n")
        else "image/jpeg"
        if payload.startswith(b"\xff\xd8")
        else "image/webp"
        if payload[:4] == b"RIFF" and payload[8:12] == b"WEBP"
        else "image/svg+xml"
    )
    source = prepare_source(payload, media, byte_budget=byte_budget)
    check_cancel(cancelled)
    digest = hashlib.sha256(payload).hexdigest()
    asset = Asset(
        id=AssetId(new_id()),
        path="assets/data/" + digest,
        sha256=digest,
        byte_length=len(payload),
        media_type=media,
    )
    key = store.stage(asset, payload)
    if cancelled():
        store.discard_staging((key,))
        check_cancel(cancelled)
    return StagedImage(asset, key, source, path.name)
