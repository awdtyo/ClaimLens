"""Stage chain test: ingest -> claims -> plan -> report on the toy paper.

Uses sample evidence/verdicts for the report step because sandbox and
verify are Part 2's stages and still raise NotImplementedError. The
full-pipeline xfail in test_e2e.py stays until those stages land.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claimlens import ingest
from claimlens.claims import extract
from claimlens.claims.schema import Evidence, Verdict
from claimlens.pipeline import make_run_context, run_stage
from claimlens.plan import build
from claimlens.report import render


@pytest.fixture()
def isolated_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run context with isolated LLM cache and fake provider."""
    monkeypatch.setenv("CLAIMLENS_PROVIDER", "fake")
    monkeypatch.setenv("CLAIMLENS_NO_SLEEP", "1")
    monkeypatch.setenv("CLAIMLENS_CACHE_DIR", str(tmp_path / "llm_cache"))
    return make_run_context("chain-test", runs_root=tmp_path / "runs")


def test_ingest_claims_plan_chain(isolated_run, fixtures_dir: Path) -> None:  # type: ignore[no-untyped-def]
    parsed = run_stage("ingest", isolated_run, {"pdf_path": fixtures_dir / "toy_paper.pdf"})
    claims = run_stage("claims", isolated_run, {"parsed": parsed})
    plan = run_stage("plan", isolated_run, {"parsed": parsed, "claims": claims})
    assert [claim.id for claim in claims] == ["c1", "c2", "c3"]
    assert {item.claim_id for item in plan.items} == {"c1", "c2", "c3"}
    assert all(assumption.reason for assumption in plan.assumptions)
    run_dir = Path(isolated_run.run_dir)  # type: ignore[arg-type]
    assert (run_dir / "01_ingest.json").exists()
    assert (run_dir / "02_claims.json").exists()
    assert (run_dir / "03_plan.json").exists()


def test_chain_report_renders(isolated_run, fixtures_dir: Path) -> None:  # type: ignore[no-untyped-def]
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    claims = extract.extract_claims(parsed, isolated_run)
    plan = build.build_plan(parsed, claims, isolated_run)
    evidence = [
        Evidence.model_validate(item)
        for item in json.loads((fixtures_dir / "sample_evidence.json").read_text(encoding="utf-8"))
    ]
    verdicts = [
        Verdict.model_validate(item)
        for item in json.loads((fixtures_dir / "sample_verdicts.json").read_text(encoding="utf-8"))
    ]
    md_path = render.render_report(claims, plan, evidence, verdicts, isolated_run)
    text = md_path.read_text(encoding="utf-8")
    assert "c1" in text and "partially replicated" in text


def test_full_pipeline_still_blocked_at_sandbox(isolated_run, fixtures_dir: Path) -> None:  # type: ignore[no-untyped-def]
    """Documents the Task 5 frontier: sandbox (Part 2) is not implemented."""
    from claimlens.pipeline import run_pipeline

    with pytest.raises(NotImplementedError):
        run_pipeline(
            pdf_path=fixtures_dir / "toy_paper.pdf",
            run_id="chain-blocked",
            runs_root=Path(isolated_run.run_dir).parent,  # type: ignore[arg-type]
        )
