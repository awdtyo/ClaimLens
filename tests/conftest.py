"""Shared pytest fixtures and environment defaults."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("CLAIMLENS_PROVIDER", "fake")
os.environ.setdefault("CLAIMLENS_NO_SLEEP", "1")


@pytest.fixture()
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture()
def fake_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """ClaimLensConfig using the fake provider with an isolated cache."""
    from claimlens.config import ClaimLensConfig

    monkeypatch.setenv("CLAIMLENS_PROVIDER", "fake")
    monkeypatch.setenv("CLAIMLENS_NO_SLEEP", "1")
    monkeypatch.setenv("CLAIMLENS_CACHE_DIR", str(tmp_path / "llm_cache"))
    return ClaimLensConfig.from_env()
