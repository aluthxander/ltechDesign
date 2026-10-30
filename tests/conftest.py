"""Tests never write project preferences/recovery into the actual user's profile."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_project_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LTECHDESIGN_DATA_DIR", str(tmp_path / "user-data"))
