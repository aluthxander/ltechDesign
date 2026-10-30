"""Installed/frozen raster spike. Private to --smoke; never an editor content workflow."""

import threading
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Literal
from uuid import uuid4

from ltechdesign.assets import BlobStore
from ltechdesign.commands import Create, Dispatcher, Request
from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.models import DocumentSession, Fill, Style
from ltechdesign.persistence import read_archive

from .contracts import TERMINAL, ExportOptions, ExportTarget
from .service import ExportService


def run(output: Path, source: Path | None = None) -> dict[str, object]:
    output = output / str(uuid4())
    output.mkdir(parents=True, exist_ok=True)
    store = BlobStore()
    if source is not None:
        with source.open("rb") as stream:
            loaded = read_archive(stream)
        admission = store.admit(loaded.project.assets.assets, loaded.blobs)
        snapshot = DocumentSession(project=loaded.project)
    else:
        dispatcher = Dispatcher(DocumentSession(project=create_project("Raster spike")))
        board = create_node(
            "artboard", dispatcher.snapshot.project.document.pages[0].id, width=180, height=120
        )
        leaf = replace(
            create_node("ellipse", board.page_id, width=100, height=80),
            parent_id=board.id,
            x=10,
            y=10,
            style=Style(fill=Fill(color="#3080D080")),
        )
        snapshot = dispatcher.snapshot
        result = dispatcher.dispatch(
            Request(
                session_id=snapshot.session_id,
                expected_revision=0,
                request_id="spike",
                action_name="Spike fixture",
                source="GUI",
                operations=(Create(node=board), Create(node=leaf)),
            ),
            client_id="spike",
        )
        if not result.ok:
            raise RuntimeError(result.error)
        snapshot = dispatcher.snapshot
        admission = store.pin(())
    service = ExportService(allowed_roots=(output,))
    results = []
    try:
        formats: tuple[tuple[Literal["png", "jpg", "webp"], bool], ...] = (
            ("png", False),
            ("jpg", False),
            ("webp", False),
            ("webp", True),
        )
        for format, lossless in formats:
            options = ExportOptions(
                str(output),
                ExportTarget("all_artboards"),
                format=format,
                background="#F8F0E0" if format == "jpg" else None,
                lossless=lossless,
                pattern="{artboard}-{index}-" + ("lossless" if lossless else format),
            )
            job = service.submit(
                snapshot,
                store,
                options,
                expected_revision=snapshot.revision,
                request_id=format + str(lossless),
            )
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                status = service.get_job_status(job.id)
                if status.state in TERMINAL:
                    break
                threading.Event().wait(0.01)
            if status.state != "succeeded":
                raise RuntimeError(status)
            results.append(asdict(status))
        return {"raster_export": True, "jobs": results}
    finally:
        admission.release()
        service.shutdown()
