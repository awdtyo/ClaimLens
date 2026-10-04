"""Claim extraction tests: normalization, retry, source_ref rejection, chunking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from claimlens import ingest
from claimlens.claims import extract
from claimlens.claims.extract import ClaimDraft, normalize_tolerance, normalize_value
from claimlens.claims.schema import Claim
from claimlens.pipeline import make_run_context


@pytest.fixture()
def isolated_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run context with isolated LLM cache and fake provider."""
    monkeypatch.setenv("CLAIMLENS_PROVIDER", "fake")
    monkeypatch.setenv("CLAIMLENS_NO_SLEEP", "1")
    monkeypatch.setenv("CLAIMLENS_CACHE_DIR", str(tmp_path / "llm_cache"))
    return make_run_context("claims-test", runs_root=tmp_path / "runs")


def test_toy_paper_matches_sample_claims(isolated_run, fixtures_dir: Path) -> None:  # type: ignore[no-untyped-def]
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    claims = extract.extract_claims(parsed, isolated_run)
    expected = json.loads((fixtures_dir / "sample_claims.json").read_text(encoding="utf-8"))
    assert [claim.model_dump(mode="json") for claim in claims] == expected


def test_every_claim_has_page_and_valid_source(isolated_run, fixtures_dir: Path) -> None:  # type: ignore[no-untyped-def]
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    claims = extract.extract_claims(parsed, isolated_run)
    known = {section.id for section in parsed.sections} | {table.id for table in parsed.tables}
    assert claims
    for claim in claims:
        assert claim.page, f"claim {claim.id} is missing a page"
        assert claim.source_ref in known


def test_normalize_value() -> None:
    assert normalize_value("91.2%", None) == pytest.approx(0.912)
    assert normalize_value(91.2, "percent") == pytest.approx(0.912)
    assert normalize_value(3.2, "percentage_points") == pytest.approx(0.032)
    assert normalize_value(2.0, "ratio") == pytest.approx(2.0)
    assert normalize_value(800, "count") == pytest.approx(800)
    assert normalize_value(None, "percent") is None
    assert normalize_value("not a number", "percent") is None


def test_normalize_tolerance() -> None:
    assert normalize_tolerance(0.02) == pytest.approx(0.02)
    assert normalize_tolerance(None) == pytest.approx(0.01)
    assert normalize_tolerance(0.0) == pytest.approx(0.01)
    assert normalize_tolerance(-1.0) == pytest.approx(0.01)


def test_invalid_output_retries_then_succeeds(
    isolated_run,
    fixtures_dir: Path,
    monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
) -> None:
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    canned = json.loads((fixtures_dir / "fake_llm_responses.json").read_text(encoding="utf-8"))
    calls = {"count": 0}
    gateway = isolated_run.llm
    real_complete = gateway.complete  # type: ignore[union-attr]

    def flaky(task: str, messages, schema=None, tools=None, role="agent"):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        if task == "extract_claims" and calls["count"] == 1:
            return {"claims": [{"text": 123, "source_ref": "t1"}]}
        return real_complete(task, messages, schema=schema, tools=tools, role=role)

    monkeypatch.setattr(gateway, "complete", flaky)
    claims = extract.extract_claims(parsed, isolated_run)
    assert calls["count"] >= 2
    assert [claim.id for claim in claims] == ["c1", "c2", "c3"]
    assert canned["extract_claims"]["claims"][0]["text"] == claims[0].text


def test_persistently_invalid_output_raises(
    isolated_run,
    fixtures_dir: Path,
    monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
) -> None:
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    gateway = isolated_run.llm

    def always_bad(task: str, messages, schema=None, tools=None, role="agent"):  # type: ignore[no-untyped-def]
        return {"claims": [{"text": 123}]}

    monkeypatch.setattr(gateway, "complete", always_bad)
    with pytest.raises(ValueError, match="stayed invalid"):
        extract.extract_claims(parsed, isolated_run)


def test_bad_source_ref_rejected(
    isolated_run,
    fixtures_dir: Path,
    monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
) -> None:
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    canned = json.loads((fixtures_dir / "fake_llm_responses.json").read_text(encoding="utf-8"))
    bad = {"text": "Ghost claim with no source.", "source_ref": "table-99"}
    good = canned["extract_claims"]["claims"]
    gateway = isolated_run.llm

    def with_ghost(task: str, messages, schema=None, tools=None, role="agent"):  # type: ignore[no-untyped-def]
        assert task == "extract_claims"
        return {"claims": [*good, bad]}

    monkeypatch.setattr(gateway, "complete", with_ghost)
    claims = extract.extract_claims(parsed, isolated_run)
    assert all(claim.source_ref != "table-99" for claim in claims)
    assert [claim.id for claim in claims] == ["c1", "c2", "c3"]


def test_chunking_merges_duplicate_claims(
    isolated_run,
    fixtures_dir: Path,
    monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
) -> None:
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    monkeypatch.setattr(isolated_run.config, "max_context", 20)
    prompts = extract.chunk_prompts(parsed, isolated_run)
    assert len(prompts) == len(parsed.sections)
    claims = extract.extract_claims(parsed, isolated_run)
    assert [claim.id for claim in claims] == ["c1", "c2", "c3"]


def test_draft_validation_requires_text_and_source() -> None:
    draft = ClaimDraft.model_validate({"text": "X.", "source_ref": "t1"})
    assert draft.testable is True
    assert draft.reported_value is None
    with pytest.raises(ValidationError):
        ClaimDraft.model_validate({"text": "X."})


def test_claims_fixture_validates(fixtures_dir: Path) -> None:
    data = json.loads((fixtures_dir / "sample_claims.json").read_text(encoding="utf-8"))
    claims = [Claim.model_validate(item) for item in data]
    assert all(claim.tolerance and claim.tolerance > 0 for claim in claims)
