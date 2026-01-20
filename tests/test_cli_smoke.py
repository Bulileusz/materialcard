"""CLI smoke tests."""

import subprocess
import sys

from typer.testing import CliRunner

from materialcard.cli import app


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_module_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "materialcard", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
