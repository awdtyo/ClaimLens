"""Verification tests (Part 2): deterministic, no Docker, no model calls."""

from __future__ import annotations

from pathlib import Path

from claimlens.claims.schema import Claim, Evidence
from claimlens.verify import compare as compare_mod


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
