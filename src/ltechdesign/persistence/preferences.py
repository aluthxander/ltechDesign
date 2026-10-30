"""Small per-user project catalogue; never a source for restoring document content."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def user_data_path() -> Path:
    override = os.environ.get("LTECHDESIGN_DATA_DIR")
    if override:
        return Path(override).absolute()
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "ltechDesign Studio"


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".settings-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class Preferences:
    """Last successful local preference write wins; projects have independent writer locks."""

    def __init__(self, root: Path) -> None:
        self.path = root / "preferences.json"

    def _read(self) -> dict[str, Any]:
        try:
            if self.path.stat().st_size > 65536:
                return {}
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    @property
    def autosave_seconds(self) -> int:
        value = self._read().get("autosave_seconds", 120)
        return value if type(value) is int and (value == 0 or 10 <= value <= 3600) else 120

    def set_autosave(self, seconds: int) -> None:
        if type(seconds) is not int or not (seconds == 0 or 10 <= seconds <= 3600):
            raise ValueError("Autosave: 0 (off) or 10–3600 seconds")
        value = self._read()
        value["autosave_seconds"] = seconds
        atomic_json(self.path, value)

    @property
    def recent(self) -> tuple[str, ...]:
        value = self._read().get("recent", [])
        if not isinstance(value, list):
            return ()
        return tuple(dict.fromkeys(p for p in value if isinstance(p, str) and len(p) < 4096))[:12]

    def remember(self, path: Path) -> None:
        value = self._read()
        value["recent"] = [str(path), *(p for p in self.recent if p != str(path))][:12]
        atomic_json(self.path, value)
