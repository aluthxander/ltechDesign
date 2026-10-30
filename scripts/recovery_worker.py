"""Segment 14 test harness: real Qt editor process with controlled crash barriers."""

import json
import os
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QApplication, QFileDialog

from ltechdesign.commands import Create, Move
from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.codec import semantic_content
from ltechdesign.ui.window import StudioWindow


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value), flush=True)


def main() -> None:
    def offline(event: str, arguments: tuple[Any, ...]) -> None:
        if event in ("socket.connect", "socket.getaddrinfo"):
            raise RuntimeError("Network disabled in the portable-project proof")

    sys.addaudithook(offline)
    app = QApplication([])
    window = StudioWindow(data_dir=Path(sys.argv[1]))
    window.projects.timer.stop()
    errors: list[Exception] = []

    def show_error(error: Exception) -> None:
        errors.append(error)

    window.show_error = show_error  # type: ignore[method-assign]
    window.show()

    def wait() -> None:
        deadline = time.monotonic() + 30
        while window.busy and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.001)
        if window.busy:
            raise TimeoutError("Persistence job")
        if errors:
            raise errors.pop(0)

    emit({"ready": True, "pid": os.getpid()})
    try:
        for line in sys.stdin:
            command = json.loads(line)
            try:
                op = command["op"]
                if op == "new":
                    window.job(
                        lambda: window.prepare_admission(
                            window.service.new(create_project("Unnamed crash draft"), {})
                        ),
                        window.admit,
                    )
                    wait()
                    tab = window.current
                    assert tab
                    board = create_node(
                        "artboard",
                        tab.dispatcher.snapshot.project.document.pages[0].id,
                        width=320,
                        height=200,
                    )
                    assert window.execute(tab, (Create(node=board),))
                elif op == "open":
                    window.open_path(command["path"])
                    wait()
                elif op == "restore":
                    offers = window.projects.recovery.scan()
                    assert offers
                    offer = offers[0]
                    window.projects.restore(offer, offer.entries[0])
                    wait()
                    for other in offers[1:]:
                        other.release()
                elif op == "edit":
                    tab = window.current
                    assert tab
                    node = next(
                        n
                        for n in tab.dispatcher.snapshot.project.document.nodes.values()
                        if n.parent_id is None
                    )
                    assert window.execute(tab, (Move(node_id=node.id, dx=3, dy=0),))
                elif op in ("autosave", "pause_autosave"):
                    if op == "pause_autosave":
                        from ltechdesign.persistence import recovery

                        original = recovery.write_archive  # type: ignore[attr-defined]

                        def pause(
                            *args: Any, writer: Callable[..., Any] = original, **kwargs: Any
                        ) -> None:
                            writer(*args, **kwargs)
                            emit({"paused_before_publication": True})
                            threading.Event().wait(60)

                        recovery.write_archive = pause  # type: ignore[attr-defined]
                    window.projects.autosave()
                    wait()
                elif op == "save":
                    target = command["path"]
                    QFileDialog.getSaveFileName = lambda *a, dest=target, **k: (dest, "")  # type: ignore[method-assign]
                    window.save_document(as_new=True)
                    wait()
                elif op == "exit":
                    for tab in tuple(window.documents):
                        window.projects.closed(tab.dispatcher.snapshot.session_id)
                        tab.dispatcher.close()
                        window.service.close(tab.handle)
                    window.documents.clear()
                    window.close()
                    emit({"ok": True})
                    break
                else:
                    raise ValueError(op)
                tab = window.current
                assert tab
                emit(
                    {
                        "ok": True,
                        "revision": tab.dispatcher.snapshot.revision,
                        "session_id": tab.dispatcher.snapshot.session_id,
                        "autosaved_revision": tab.autosaved_revision,
                        "content": semantic_content(tab.dispatcher.snapshot.project),
                        "dirty": tab.dispatcher.dirty,
                        "undo_count": len(tab.dispatcher.undo_history),
                    }
                )
            except Exception as error:
                emit({"ok": False, "error": str(error)})
    finally:
        window.executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
