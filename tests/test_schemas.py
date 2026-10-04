"""Fixture files must validate against the pydantic schemas."""

from __future__ import annotations

import json
from pathlib import Path

from claimlens.claims.schema import Claim, Evidence, ParsedPaper, Plan, Verdict


def _load(fixtures_dir: Path, name: str):
    with (fixtures_dir / name).open(encoding="utf-8") as f:
        return json.load(f)


def test_sample_parsed_validates(fixtures_dir: Path) -> None:
    parsed = ParsedPaper.model_validate(_load(fixtures_dir, "sample_parsed.json"))
    assert parsed.title
    assert len(parsed.sections) == 4
    sources = [table.source for table in parsed.tables]
    assert sources.count("text") == 1
    assert sources.count("vision") == 1


def test_sample_claims_validate(fixtures_dir: Path) -> None:
    claims = [Claim.model_validate(item) for item in _load(fixtures_dir, "sample_claims.json")]
    assert len(claims) >= 1
    for claim in claims:
        assert claim.source_ref, f"claim {claim.id} needs a real source_ref"


def test_sample_plan_validates(fixtures_dir: Path) -> None:
    plan = Plan.model_validate(_load(fixtures_dir, "sample_plan.json"))
    assert plan.items
    for assumption in plan.assumptions:
        assert assumption.reason, "no assumption may have an empty reason"


def test_sample_evidence_validates(fixtures_dir: Path) -> None:
    evidence = [
        Evidence.model_validate(item) for item in _load(fixtures_dir, "sample_evidence.json")
    ]
    assert evidence


def test_sample_verdicts_validate(fixtures_dir: Path) -> None:
    verdicts = [
        Verdict.model_validate(item) for item in _load(fixtures_dir, "sample_verdicts.json")
    ]
    assert verdicts


def test_fixtures_are_consistent(fixtures_dir: Path) -> None:
    claims = {c["id"] for c in _load(fixtures_dir, "sample_claims.json")}
    plan = _load(fixtures_dir, "sample_plan.json")
    evidence = _load(fixtures_dir, "sample_evidence.json")
    verdicts = _load(fixtures_dir, "sample_verdicts.json")
    for item in plan["items"]:
        assert item["claim_id"] in claims
    for item in evidence:
        assert item["claim_id"] in claims
    assert {v["claim_id"] for v in verdicts} == claims
