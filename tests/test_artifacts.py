"""Artifact save/load round trip."""

from __future__ import annotations

from pathlib import Path

from claimlens import artifacts
from claimlens.claims.schema import ParsedPaper


def test_artifact_round_trip(tmp_path: Path, fixtures_dir: Path) -> None:
    import json

    with (fixtures_dir / "sample_parsed.json").open(encoding="utf-8") as f:
        data = json.load(f)
    parsed = ParsedPaper.model_validate(data)
    run_dir = tmp_path / "runs" / "toy"
    saved = artifacts.save_artifact(run_dir, "ingest", parsed)
    assert saved == run_dir / "01_ingest.json"
    loaded = artifacts.load_artifact(run_dir, "ingest")
    assert ParsedPaper.model_validate(loaded) == parsed


def test_artifact_list_round_trip(tmp_path: Path, fixtures_dir: Path) -> None:
    import json

    from claimlens.claims.schema import Claim

    with (fixtures_dir / "sample_claims.json").open(encoding="utf-8") as f:
        data = json.load(f)
    claims = [Claim.model_validate(item) for item in data]
    run_dir = tmp_path / "runs" / "toy"
    artifacts.save_artifact(run_dir, "claims", claims)
    loaded = artifacts.load_artifact(run_dir, "claims")
    assert [Claim.model_validate(item) for item in loaded] == claims
