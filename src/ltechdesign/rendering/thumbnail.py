"""Bounded project cover via the shared renderer in a separate QGui process."""

import logging
import multiprocessing
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from ltechdesign.domain.models import Project
from ltechdesign.persistence.archive import read_archive, write_archive


def render_file(source: str, target: str) -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QGuiApplication

    from ltechdesign.domain.geometry import local_matrix
    from ltechdesign.rendering.drawing import local_visual, render_image, transform
    from ltechdesign.rendering.fonts import FontResolver

    app = QGuiApplication([])
    with Path(source).open("rb") as stream:
        loaded = read_archive(stream)
    document = loaded.project.document
    resolver = FontResolver()
    try:
        resources = resolver.resolve(loaded.project, loaded.blobs)
        bounds = QRectF()
        roots = document.pages[0].root_ids
        for page in document.pages:
            candidate = QRectF()
            for key in page.root_ids:
                candidate = candidate.united(
                    transform(local_matrix(document.nodes[key])).mapRect(
                        local_visual(document, key)
                    )
                )
            if not candidate.isEmpty():
                roots, bounds = page.root_ids, candidate
                break
        if bounds.isEmpty():
            bounds = QRectF(0, 0, 320, 200)
        image = render_image(
            document,
            roots,
            bounds,
            min(320 / bounds.width(), 240 / bounds.height()),
            resources=resources,
        )
        if not image.save(target):
            raise OSError("Thumbnail encoding failed")
    finally:
        resolver.close()
    app.quit()


def generate(project: Project, blobs: Mapping[str, bytes]) -> bytes | None:
    """Optional preview failure never prevents saving the editable project."""
    try:
        with tempfile.TemporaryDirectory(prefix="ltechdesign-preview-") as directory:
            source, target = Path(directory) / "input.ltechdesign", Path(directory) / "cover.png"
            with source.open("w+b") as stream:
                write_archive(stream, project, blobs)
            child = multiprocessing.get_context("spawn").Process(
                target=render_file, args=(str(source), str(target)), daemon=True
            )
            child.start()
            try:
                child.join(20)
                if child.is_alive():
                    child.terminate()
                    child.join(5)
                if child.exitcode == 0 and target.is_file():
                    return target.read_bytes()
            finally:
                if child.is_alive():
                    child.kill()
                    child.join()
                child.close()
    except Exception:
        logging.getLogger(__name__).exception("Project thumbnail unavailable")
    return None
