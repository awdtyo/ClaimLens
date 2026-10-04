"""CLI smoke tests."""

from __future__ import annotations

from typer.testing import CliRunner

from claimlens.cli import app

runner = CliRunner()


def test_help_runs() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output


def test_stage_help_runs() -> None:
    result = runner.invoke(app, ["stage", "--help"])
    assert result.exit_code == 0
