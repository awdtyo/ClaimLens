"""Plan tests: toy match, gaps, spec validation, planner retry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claimlens import ingest
from claimlens.claims import extract
from claimlens.claims.schema import Claim, Plan
from claimlens.pipeline import make_run_context
from claimlens.plan import build, gaps, spec


@pytest.fixture()
def isolated_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run context with isolated LLM cache and fake provider."""
    monkeypatch.setenv("CLAIMLENS_PROVIDER", "fake")
    monkeypatch.setenv("CLAIMLENS_NO_SLEEP", "1")
    monkeypatch.setenv("CLAIMLENS_CACHE_DIR", str(tmp_path / "llm_cache"))
    return make_run_context("plan-test", runs_root=tmp_path / "runs")


@pytest.fixture()
def toy_inputs(isolated_run, fixtures_dir: Path):  # type: ignore[no-untyped-def]
    """(parsed, claims, run) for the toy paper."""
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    claims = extract.extract_claims(parsed, isolated_run)
    return parsed, claims, isolated_run


def test_toy_paper_matches_sample_plan(toy_inputs, fixtures_dir: Path) -> None:  # type: ignore[no-untyped-def]
    parsed, claims, run = toy_inputs
    plan = build.build_plan(parsed, claims, run)
    expected = json.loads((fixtures_dir / "sample_plan.json").read_text(encoding="utf-8"))
    assert plan.model_dump(mode="json") == expected


def test_no_assumption_has_empty_reason(toy_inputs) -> None:  # type: ignore[no-untyped-def]
    parsed, claims, run = toy_inputs
    plan = build.build_plan(parsed, claims, run)
    assert plan.assumptions
    for assumption in plan.assumptions:
        assert assumption.reason, "no assumption may have an empty reason"


def test_find_gaps_reports_stated_and_missing(toy_inputs) -> None:  # type: ignore[no-untyped-def]
    parsed, claims, _ = toy_inputs
    found = gaps.find_gaps(parsed, claims)
    by_detail = {gap.detail: gap for gap in found}
    assert by_detail["random seed"].stated_value is not None
    assert "0" in (by_detail["random seed"].stated_value or "")
    assert by_detail["training data subsample for the scaled run"].stated_value is None
    assert all(gap.context for gap in found)


def test_extract_stated_settings(toy_inputs) -> None:  # type: ignore[no-untyped-def]
    parsed, _, _ = toy_inputs
    stated = gaps.extract_stated_settings(parsed)
    assert "random seed" in stated
    assert "learning rate" in stated
    assert "batch size" in stated


def test_write_spec_defaults_scale_reason() -> None:
    claim = Claim(id="c1", text="X.", source_ref="t1")
    item = spec.write_spec(claim, {"steps": ["Do it."], "scale_factor": 0.5, "config": {}})
    assert item.claim_id == "c1"
    assert item.scale_reason, "scale reason must never be empty"


def test_write_spec_rejects_bad_specs() -> None:
    claim = Claim(id="c1", text="X.", source_ref="t1")
    with pytest.raises(ValueError):
        spec.write_spec(claim, {"claim_id": "c9", "steps": ["Do it."]})
    with pytest.raises(ValueError):
        spec.write_spec(claim, {"steps": []})
    with pytest.raises(ValueError):
        spec.write_spec(claim, {"steps": ["Do it."], "scale_factor": 2.0})
    with pytest.raises(TypeError):
        spec.write_spec(claim, {"steps": ["Do it."], "config": [1]})


def test_empty_reason_triggers_retry(toy_inputs, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    parsed, claims, run = toy_inputs
    gateway = run.llm
    real_complete = gateway.complete  # type: ignore[union-attr]
    calls = {"count": 0}

    def flaky(task: str, messages, schema=None, tools=None, role="agent"):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        if task == "build_plan" and calls["count"] == 1:
            return {
                "assumptions": [
                    {"detail": "d", "value_chosen": "v", "reason": "", "confidence": "low"}
                ],
                "items": [],
            }
        return real_complete(task, messages, schema=schema, tools=tools, role=role)

    monkeypatch.setattr(gateway, "complete", flaky)
    plan = build.build_plan(parsed, claims, run)
    assert calls["count"] >= 2
    assert all(a.reason for a in plan.assumptions)


def test_missing_item_for_claim_raises(toy_inputs, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    parsed, claims, run = toy_inputs
    gateway = run.llm

    def drop_c3(task: str, messages, schema=None, tools=None, role="agent"):  # type: ignore[no-untyped-def]
        assert task == "build_plan"
        return {
            "assumptions": [
                {
                    "detail": "Random seed for training",
                    "value_chosen": "0",
                    "reason": "Stated in Section 2.",
                    "confidence": "high",
                }
            ],
            "items": [
                {
                    "claim_id": "c1",
                    "steps": ["Train."],
                    "scale_factor": 0.1,
                    "scale_reason": "Cheap.",
                    "config": {},
                }
            ],
        }

    monkeypatch.setattr(gateway, "complete", drop_c3)
    with pytest.raises(ValueError, match="without items"):
        build.build_plan(parsed, claims, run)


def test_plan_fixture_validates(fixtures_dir: Path) -> None:
    data = json.loads((fixtures_dir / "sample_plan.json").read_text(encoding="utf-8"))
    plan = Plan.model_validate(data)
    assert all(item.scale_reason for item in plan.items)
