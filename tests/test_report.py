"""Report tests: readable Markdown and Verdict-schema JSON."""

from __future__ import annotations

import json
from pathlib import Path

from claimlens.claims.schema import Claim, Evidence, Plan, Verdict
from claimlens.pipeline import make_run_context
from claimlens.report import render


def _load_fixtures(fixtures_dir: Path) -> tuple[list[Claim], Plan, list[Evidence], list[Verdict]]:
    claims = [
        Claim.model_validate(item)
        for item in json.loads((fixtures_dir / "sample_claims.json").read_text(encoding="utf-8"))
    ]
    plan = Plan.model_validate(
        json.loads((fixtures_dir / "sample_plan.json").read_text(encoding="utf-8"))
    )
    evidence = [
        Evidence.model_validate(item)
        for item in json.loads((fixtures_dir / "sample_evidence.json").read_text(encoding="utf-8"))
    ]
    verdicts = [
        Verdict.model_validate(item)
        for item in json.loads((fixtures_dir / "sample_verdicts.json").read_text(encoding="utf-8"))
    ]
    return claims, plan, evidence, verdicts


def test_report_readable_without_other_files(tmp_path: Path, fixtures_dir: Path) -> None:
    claims, plan, evidence, verdicts = _load_fixtures(fixtures_dir)
    run = make_run_context("report-test", runs_root=tmp_path / "runs")
    md_path = render.render_report(claims, plan, evidence, verdicts, run)
    assert md_path.exists()
    assert md_path.name == "report.md"
    text = md_path.read_text(encoding="utf-8")
    # Summary table plus one section per claim.
    assert "| Claim | Reported | Measured | Verdict |" in text
    for claim in claims:
        assert claim.id in text
        assert claim.text in text
    for verdict in verdicts:
        assert verdict.status in text
        assert verdict.rationale in text
    # Numbers side by side.
    assert "0.912" in text
    assert "90.8" in text
    # Assumptions with reasons.
    for assumption in plan.assumptions:
        assert assumption.detail in text
        assert assumption.value_chosen in text
    # Scale limitations and log links.
    assert "cannot refute the paper" in text
    assert "04_sandbox_e1.log" in text
    assert "llm_log.jsonl" in text


def test_report_json_matches_verdict_schema(tmp_path: Path, fixtures_dir: Path) -> None:
    claims, plan, evidence, verdicts = _load_fixtures(fixtures_dir)
    run = make_run_context("report-json", runs_root=tmp_path / "runs")
    render.render_report(claims, plan, evidence, verdicts, run)
    report_json = Path(run.run_dir) / "report.json"  # type: ignore[arg-type]
    data = json.loads(report_json.read_text(encoding="utf-8"))
    assert [Verdict.model_validate(item) for item in data] == verdicts


def test_report_shows_assumption_effects(tmp_path: Path) -> None:
    from claimlens.claims.schema import Assumption, AssumptionEffect, PlanItem

    claims = [Claim(id="c1", text="X holds under noise.", source_ref="t1", reported_value=0.895)]
    plan = Plan(
        items=[PlanItem(claim_id="c1", steps=["Run."], scale_factor=1.0, config={})],
        assumptions=[
            Assumption(
                id="a1", detail="Random seed", value_chosen="0", reason="Stated.", confidence="high"
            )
        ],
    )
    verdicts = [
        Verdict(
            claim_id="c1",
            status="not replicated",
            rationale="Measured lower at full scale.",
            evidence_ids=["e1"],
            scaled=False,
            assumption_effects=[
                AssumptionEffect(
                    assumption_id="a1",
                    claim_id="c1",
                    alt_value="seed 1",
                    measured_value=0.824,
                    delta=0.003,
                )
            ],
        )
    ]
    evidence = [Evidence(id="e1", claim_id="c1", method="docker", measured_value=0.821)]
    text = render.render_markdown(claims, plan, evidence, verdicts, "demo")
    assert "Random seed" in text
    assert "seed 1" in text
    assert "0.824" in text


def test_fmt_number() -> None:
    assert render.fmt_number(None) == "n/a"
    assert render.fmt_number(0.912) == "0.912"
