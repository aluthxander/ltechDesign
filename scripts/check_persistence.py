"""Installed-package/offline native portability smoke, with no source-tree imports."""

import argparse
import os
import tempfile
from pathlib import Path

from ltechdesign.domain import semantic_content
from ltechdesign.persistence import PersistenceService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    fixture = args.fixture.resolve(strict=True)
    scratch = args.scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    service = PersistenceService()
    source = service.open(fixture, read_only=True)
    original_cwd = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            os.chdir(directory)
            destination = Path(directory) / "portable.ltechdesign"
            service.save(source, source.admission, source.loaded.blobs, target=destination)
            service.close(source)
            moved = destination.with_name("moved.ltechdesign")
            destination.rename(moved)
            restored = service.open(moved)
            try:
                assert semantic_content(restored.loaded.project) == semantic_content(
                    source.loaded.project
                )
                assert restored.loaded.blobs == source.loaded.blobs
                assert restored.admission.session_id != source.admission.session_id
                print(
                    f"Native wheel smoke: {len(restored.loaded.project.document.pages)} pages, "
                    f"{len(restored.loaded.project.document.nodes)} editable nodes, "
                    f"{len(restored.loaded.blobs)} byte-identical blobs; changed cwd; PASS"
                )
            finally:
                service.close(restored)
                os.chdir(original_cwd)
    finally:
        os.chdir(original_cwd)
        if not source._closed:
            service.close(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
