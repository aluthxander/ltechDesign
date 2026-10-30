"""Private spawned render worker. No editor/scene objects cross the process boundary."""

import os
from multiprocessing.connection import Connection
from pathlib import Path

from ltechdesign.domain.errors import ModelError

from .contracts import ExportOptions


def render_worker(
    source: str,
    options: ExportOptions,
    connection: Connection,
    maximum: int,
    max_outputs: int,
    prefer_pillow_webp: bool,
) -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtGui import QGuiApplication

    from ltechdesign.persistence.archive import read_archive
    from ltechdesign.rendering.drawing import render_image
    from ltechdesign.rendering.exporting import plans
    from ltechdesign.rendering.fonts import FontResolver

    from .encoding import encode

    app = QGuiApplication([])
    resolver = FontResolver()
    try:
        connection.send(("progress", 0.03, "load_snapshot"))
        with Path(source).open("rb") as stream:
            loaded = read_archive(stream)
        targets = plans(loaded.project, options, maximum, max_outputs)
        metadata = [
            dict(
                name=p.name,
                width=p.width,
                height=p.height,
                bounds=(p.bounds.x(), p.bounds.y(), p.bounds.width(), p.bounds.height()),
            )
            for p in targets
        ]
        connection.send(("plans", metadata))
        temporary = connection.recv()
        resources = resolver.resolve(loaded.project, loaded.blobs)
        for index, (plan, target) in enumerate(zip(targets, temporary, strict=True)):
            connection.send(("progress", (index + 0.1) / len(targets), "drawing"))
            try:
                notes: list[str] = []
                image = render_image(
                    plan.document,
                    plan.roots,
                    plan.bounds,
                    options.scale,
                    resources=plan.resources(resources),
                    notes=notes,
                    dimensions=(plan.width, plan.height) if options.width is not None else None,
                )
                connection.send(("progress", (index + 0.6) / len(targets), "encoding"))
                encoder, extra = encode(
                    image, Path(target), options, prefer_pillow_webp=prefer_pillow_webp
                )
                del image
                connection.send(("ready", index, encoder, tuple(dict.fromkeys([*notes, *extra]))))
            except (ModelError, OSError, ValueError) as error:
                code = error.code if isinstance(error, ModelError) else "io_error"
                connection.send(("output_error", index, code, str(error)))
            # Parent owns commit/cancellation; do not proceed until acknowledged.
            connection.recv()
        connection.send(("done",))
    except (ModelError, OSError, ValueError) as error:
        code = error.code if isinstance(error, ModelError) else "io_error"
        connection.send(("error", code, str(error)))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        resolver.close()
        connection.close()
        app.quit()
