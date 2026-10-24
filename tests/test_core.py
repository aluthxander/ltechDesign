import logging
import subprocess
import sys
from pathlib import Path

import pytest

from ltechdesign import __version__
from ltechdesign.cli import main
from ltechdesign.logging_config import configure_logging

pytestmark = pytest.mark.core
ROOT = Path(__file__).resolve().parents[1]


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as result:
        main(["--version"])
    assert result.value.code == 0
    assert capsys.readouterr().out.strip() == f"ltechdesign {__version__}"


def test_cli_rejects_unavailable_subsystem() -> None:
    with pytest.raises(SystemExit) as result:
        main(["render"])
    assert result.value.code == 2


def test_cli_does_not_import_qt() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; from ltechdesign.cli import main; "
            "assert not any(k.startswith('PySide6') for k in sys.modules); main(['--version'])",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_logging_is_idempotent_and_keeps_root_untouched() -> None:
    root_handlers = logging.getLogger().handlers.copy()
    logger = configure_logging()
    count = len(logger.handlers)
    assert configure_logging() is logger
    assert len(logger.handlers) == count == 1
    assert not logger.propagate
    assert logging.getLogger().handlers == root_handlers


def test_fixture_regeneration_and_drift_detection(tmp_path: Path) -> None:
    command = [
        sys.executable,
        str(ROOT / "scripts/generate_fixtures.py"),
        "--output",
        str(tmp_path),
    ]
    subprocess.run(command, check=True, timeout=30)
    subprocess.run([*command, "--check"], check=True, timeout=30)
    for relative in ("fonts/manifest.json", "visual/text-sample.txt"):
        assert (tmp_path / relative).read_bytes() == (
            ROOT / "tests/fixtures" / relative
        ).read_bytes()
    (tmp_path / "visual/text-sample.txt").write_text("changed", encoding="utf-8")
    assert subprocess.run([*command, "--check"], timeout=30).returncode == 1
