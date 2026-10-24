"""04A test child. JSON lines are a test harness, not an application IPC/MCP server."""

import json
import os
import sys
from pathlib import Path
from typing import Any, BinaryIO

from ltechdesign.domain import ModelError
from ltechdesign.persistence import FileHandle, PersistenceService


def emit(result: dict[str, Any]) -> None:
    print(json.dumps({"pid": os.getpid(), **result}), flush=True)


def main() -> None:
    service = PersistenceService()
    handles: dict[str, FileHandle] = {}
    held: BinaryIO | None = None
    emit({"ready": True})
    try:
        for line in sys.stdin:
            command = json.loads(line)
            op = command["op"]
            try:
                key = command.get("key", "main")
                if op == "open":
                    handle = service.open(
                        command["path"], read_only=command.get("read_only", False)
                    )
                    handles[key] = handle
                    emit(
                        {
                            "ok": True,
                            "session_id": handle.admission.session_id,
                            "document_id": handle.admission.project.document.document_id,
                            "revision": handle.admission.revision,
                            "read_only": handle.read_only,
                        }
                    )
                elif op == "close":
                    service.close(handles.pop(key))
                    emit({"ok": True})
                elif op == "hold":
                    held = Path(command["path"]).open("rb")
                    emit({"ok": True})
                elif op == "release":
                    assert held is not None
                    held.close()
                    held = None
                    emit({"ok": True})
                elif op == "replace_external":
                    target = Path(command["path"])
                    temp = target.with_name(target.name + ".external.tmp")
                    temp.write_bytes(Path(command["replacement"]).read_bytes())
                    os.replace(temp, target)
                    emit({"ok": True})
                elif op == "save":
                    handle = handles[key]
                    paused = False

                    def checkpoint(pause: bool = bool(command.get("pause"))) -> bool:
                        nonlocal paused
                        if pause and not paused:
                            paused = True
                            emit({"paused": True})
                            assert json.loads(sys.stdin.readline()) == {"op": "resume"}
                        return False

                    result = service.save(
                        handle,
                        handle.admission,
                        handle.loaded.blobs,
                        target=command.get("target"),
                        overwrite=command.get("overwrite", False),
                        cancelled=checkpoint,
                    )
                    emit(
                        {
                            "ok": True,
                            "path": str(result.path),
                            "session_id": result.checkpoint.session_id,
                        }
                    )
                elif op == "exit":
                    emit({"ok": True})
                    break
                else:
                    raise ValueError(op)
            except ModelError as error:
                emit({"ok": False, "code": error.code, "reason": error.reason})
    finally:
        if held is not None:
            held.close()
        for handle in handles.values():
            if not handle._closed:
                service.close(handle)


if __name__ == "__main__":
    main()
