"""Verification tests (Part 2): deterministic, no Docker, no model calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from claimlens.claims.schema import Assumption, Claim, Evidence, Plan, PlanItem
from claimlens.verify import compare as compare_mod
from claimlens.verify import sensitivity as sensitivity_mod


def _claim(**overrides) -> Claim:  # type: ignore[no-untyped-def]
    base = {
        "id": "c1",
        "text": "Method X reaches 91.2% accuracy.",
        "source_ref": "t1",
        "metric": "accuracy",
        "reported_value": 0.912,
        "tolerance": 0.01,
    }
    base.update(overrides)
    return Claim(**base)  # type: ignore[arg-type]


def _evidence(measured: float | None, claim_id: str = "c1", eid: str = "e1") -> Evidence:
    return Evidence(
        id=eid,
        claim_id=claim_id,
        method="docker",
        measured_value=measured,
        scale_factor=1.0,
    )


def test_match_is_replicated() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.912)])
    assert outcome.status == "replicated"
    assert outcome.evidence_ids == ["e1"]
    assert outcome.scaled is False


def test_near_match_is_partially_replicated() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.925)])
    assert outcome.status == "partially replicated"


def test_mismatch_is_not_replicated() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.85)])
    assert outcome.status == "not replicated"


def test_scaled_match_is_partially_replicated_with_scale_note() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.908)], scale_factor=0.1)
    assert outcome.status == "partially replicated"
    assert outcome.scaled is True
    assert "scale" in outcome.rationale


def test_scaled_mismatch_cannot_refute() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.70)], scale_factor=0.1)
    assert outcome.status == "partially replicated"
    assert outcome.status != "not replicated"
    assert "cannot refute" in outcome.rationale


def test_scaled_run_never_fully_replicates() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.912)], scale_factor=0.1)
    assert outcome.status == "partially replicated"


def test_missing_evidence_is_untestable() -> None:
    outcome = compare_mod.compare_claim(_claim(), [])
    assert outcome.status == "untestable"
    assert outcome.reason


def test_missing_evidence_at_scale_is_untestable_at_this_scale() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(None)], scale_factor=0.1)
    assert outcome.status == "untestable at this scale"


def test_missing_reported_value_is_untestable() -> None:
    outcome = compare_mod.compare_claim(_claim(reported_value=None), [_evidence(0.9)])
    assert outcome.status == "untestable"


def test_untestable_claim_stays_untestable() -> None:
    outcome = compare_mod.compare_claim(_claim(testable=False), [_evidence(0.912)])
    assert outcome.status == "untestable"


def test_raw_percent_values_are_normalized() -> None:
    claim = _claim(reported_value=91.2)
    outcome = compare_mod.compare_claim(claim, [_evidence(91.1)])
    assert outcome.status == "replicated"
    assert "91.1%" in outcome.rationale


def test_speedup_ratio_is_not_treated_as_percent() -> None:
    claim = _claim(metric="speedup", reported_value=2.0, tolerance=0.1)
    assert compare_mod.compare_claim(claim, [_evidence(1.95)]).status == "replicated"
    assert compare_mod.compare_claim(claim, [_evidence(1.2)]).status == "not replicated"


def test_evidence_for_other_claims_is_ignored() -> None:
    outcome = compare_mod.compare_claim(_claim(), [_evidence(0.912, claim_id="c2", eid="e2")])
    assert outcome.status == "untestable"
    assert outcome.evidence_ids == []


def test_compare_module_makes_no_model_calls() -> None:
    source = Path(compare_mod.__file__).read_text(encoding="utf-8").lower()
    assert "llm" not in source
    assert "complete(" not in source


# -- sensitivity (fake runner, no Docker) --------------------------------------


def _sensitivity_plan() -> Plan:
    return Plan(
        items=[
            PlanItem(claim_id="c3", steps=["Train under noise"], scale_factor=1.0, config={}),
        ],
        assumptions=[
            Assumption(
                id="a1",
                detail="Random seed",
                value_chosen="0",
                reason="Fixed seed in the paper.",
                confidence="high",
            ),
            Assumption(
                id="a2",
                detail="Label noise rate",
                value_chosen="0.1",
                reason="Paper says 10% of labels flip.",
                confidence="medium",
            ),
        ],
    )


def _sensitivity_claim() -> Claim:
    return Claim(
        id="c3",
        text="Method X keeps accuracy under noise.",
        source_ref="s4",
        metric="accuracy_noisy",
        reported_value=0.895,
        tolerance=0.01,
    )


def _sensitivity_runner(plan: Plan, run: object) -> list[Evidence]:
    values = {assumption.value_chosen for assumption in plan.assumptions}
    if "1" in values:
        measured = 0.824
    elif "0.05" in values:
        measured = 0.84
    else:  # pragma: no cover - variants always change one assumption.
        measured = 0.821
    return [
        Evidence(id="e3", claim_id="c3", method="fake", measured_value=measured),
    ]


def test_alternate_values_are_deterministic() -> None:
    assert sensitivity_mod.alternate_value(_sensitivity_plan().assumptions[0]) == "1"
    assert sensitivity_mod.alternate_value(_sensitivity_plan().assumptions[1]) == "0.05"


def test_sensitivity_ranks_effects_by_absolute_delta(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("sensitivity", runs_root=tmp_path / "runs")
    base = [Evidence(id="e3", claim_id="c3", method="fake", measured_value=0.821)]
    effects = sensitivity_mod.run_sensitivity(
        _sensitivity_claim(), _sensitivity_plan(), base, run, _sensitivity_runner
    )
    assert [effect.assumption_id for effect in effects] == ["a2", "a1"]
    assert effects[0].alt_value == "0.05"
    assert effects[0].measured_value == pytest.approx(0.84)
    assert effects[0].delta == pytest.approx(0.019)
    assert effects[1].delta == pytest.approx(0.003)


def test_sensitivity_respects_max_reruns(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("sensitivity-cap", runs_root=tmp_path / "runs")
    base = [Evidence(id="e3", claim_id="c3", method="fake", measured_value=0.821)]
    effects = sensitivity_mod.run_sensitivity(
        _sensitivity_claim(), _sensitivity_plan(), base, run, _sensitivity_runner, max_reruns=1
    )
    assert [effect.assumption_id for effect in effects] == ["a1"]


def test_sensitivity_skips_reruns_without_measurements(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("sensitivity-empty", runs_root=tmp_path / "runs")
    base = [Evidence(id="e3", claim_id="c3", method="fake", measured_value=0.821)]
    effects = sensitivity_mod.run_sensitivity(
        _sensitivity_claim(), _sensitivity_plan(), base, run, lambda plan, run: []
    )
    assert effects == []


def test_sensitivity_needs_a_baseline_measurement(tmp_path: Path) -> None:
    from claimlens.pipeline import make_run_context

    run = make_run_context("sensitivity-nobase", runs_root=tmp_path / "runs")
    calls: list[Plan] = []
    effects = sensitivity_mod.run_sensitivity(
        _sensitivity_claim(),
        _sensitivity_plan(),
        [],
        run,
        lambda plan, run: calls.append(plan) or [],
    )
    assert effects == []
    assert calls == []


def test_sensitivity_module_makes_no_model_calls() -> None:
    source = Path(sensitivity_mod.__file__).read_text(encoding="utf-8").lower()
    assert "llm" not in source
