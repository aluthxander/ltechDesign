"""Native ZIP fixture, not an application loader. Historical JSON fixtures remain intact."""

import base64
import hashlib
import io
import json
import struct
import zlib
from dataclasses import replace
from pathlib import Path

from ltechdesign.domain import load_project
from ltechdesign.domain.codec import json_bytes
from ltechdesign.domain.models import AssetsIndex
from ltechdesign.persistence import read_archive, write_archive

ROOT = Path(__file__).resolve().parents[1]


def native_fixture() -> bytes:
    wrapper = json.loads((ROOT / "tests/fixtures/schema/nested-v1.json").read_text("utf-8"))
    payloads = {p: json_bytes(v) for p, v in wrapper["members"].items()}
    payloads.update({b["path"]: base64.b64decode(b["base64"]) for b in wrapper["asset_blobs"]})
    project = load_project(payloads)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    # Valid original RGBA bytes, independent of Qt encoder version. The old fixture's
    # PNG has a corrupt IDAT CRC; never relax production decoding to admit it.
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">2I5B", 1, 1, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\x80")) + chunk(b"IEND", b"")
    digest = hashlib.sha256(png).hexdigest()
    blobs = {a.path: payloads[a.path] for a in project.assets.assets}
    changed = {}
    assets = []
    for asset in project.assets.assets:
        if asset.media_type == "image/png":
            updated = replace(
                asset, path="assets/data/" + digest, sha256=digest, byte_length=len(png)
            )
            changed[asset.path] = updated
            blobs.pop(asset.path, None)
            blobs[updated.path] = png
            asset = updated
        assets.append(asset)
    files = tuple(
        replace(e, path=changed[e.path].path, sha256=digest, byte_length=len(png))
        if e.path in changed
        else e
        for e in project.manifest.files
    )
    project = replace(
        project,
        assets=AssetsIndex(assets=tuple(assets)),
        manifest=replace(project.manifest, files=files),
    )
    stream = io.BytesIO()
    write_archive(stream, project, blobs)
    read_archive(stream)
    return stream.getvalue()


if __name__ == "__main__":
    target = ROOT / "examples/proyek-contoh.ltechdesign"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(native_fixture())
    print(target)
