"""Deterministic result comparison (Stage 6).

Hard rule: the model never decides whether results match. Numbers are
extracted, normalized and compared in Python with explicit tolerances.
No model call is allowed in this module — it imports no model gateway.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from claimlens.claims.schema import Claim, Evidence

DEFAULT_TOLERANCE = 0.01
NEAR_MATCH_TOLERANCES = 3.0

PERCENT_METRICS = ("accur", "percent", "precis", "recall", "f1", "rate", "gain", "error")


@dataclass
class Comparison:
    """Outcome of comparing one claim against its evidence."""

    status: str
    rationale: str
    scaled: bool
    evidence_ids: list[str] = field(default_factory=list)
    reason: str | None = None


def _is_percent_metric(metric: str | None) -> bool:
    return bool(metric) and any(key in metric.lower() for key in PERCENT_METRICS)


def normalize_value(value: float, metric: str | None) -> float:
    """Normalize a measured value the same way claims are normalized.

    Percentages and percentage points pass through divided by 100
    (91.2 -> 0.912); ratios, speedups and counts pass through
    unchanged. The metric name decides which rule applies, so a 2x
    speedup is never mistaken for 200%.
    """
    if _is_percent_metric(metric) and abs(value) > 1.5:
        return value / 100.0
    return value


def _format(value: float, metric: str | None) -> str:
    if _is_percent_metric(metric):
        return f"{value * 100.0:g}%"
    return f"{value:g}"


def compare_claim(
    claim: Claim,
    evidence: list[Evidence],
    scale_factor: float = 1.0,
) -> Comparison:
    """Compare measured evidence to a claim's reported value in code.

    Args:
        claim: Claim under audit (carries ``reported_value`` and
            ``tolerance`` in normalized units).
        evidence: Measured results; only entries for this claim with a
            real ``measured_value`` count.
        scale_factor: 1.0 for full-scale runs, below 1.0 for scaled
            runs. Scaled runs can neither fully confirm nor refute: the
            strongest outcomes are ``partially replicated`` and
            ``untestable at this scale``, and the rationale states what
            the scaled run does and does not show.

    Returns:
        Comparison with a verdict status of ``replicated``,
        ``partially replicated``, ``not replicated``, ``untestable`` or
        ``untestable at this scale``.
    """
    scaled = scale_factor < 1.0
    usable = [
        item
        for item in evidence
        if item.claim_id == claim.id
        and item.measured_value is not None
        and math.isfinite(item.measured_value)
    ]
    evidence_ids = [item.id for item in usable]

    if not claim.testable:
        return Comparison(
            status="untestable at this scale" if scaled else "untestable",
            rationale=f"Claim {claim.id} is marked untestable; no experiment can resolve it.",
            scaled=scaled,
            evidence_ids=evidence_ids,
            reason="Claim is marked untestable.",
        )
    if claim.reported_value is None or not math.isfinite(claim.reported_value):
        return Comparison(
            status="untestable at this scale" if scaled else "untestable",
            rationale=f"Claim {claim.id} has no reported number to compare against.",
            scaled=scaled,
            evidence_ids=evidence_ids,
            reason="No reported value for this claim.",
        )
    if not usable:
        return Comparison(
            status="untestable at this scale" if scaled else "untestable",
            rationale=(
                f"Claim {claim.id} has no measured evidence"
                + (" at this scale." if scaled else ".")
            ),
            scaled=scaled,
            evidence_ids=[],
            reason="No measured evidence for this claim.",
        )

    measured_raw = usable[0].measured_value
    assert measured_raw is not None
    reported_raw = claim.reported_value
    assert reported_raw is not None
    measured = normalize_value(measured_raw, claim.metric)
    reported = normalize_value(reported_raw, claim.metric)
    tolerance = claim.tolerance if claim.tolerance is not None else DEFAULT_TOLERANCE
    if not math.isfinite(tolerance) or tolerance < 0:
        tolerance = DEFAULT_TOLERANCE
    diff = abs(measured - reported)
    shown_measured = _format(measured, claim.metric)
    shown_reported = _format(reported, claim.metric)

    if diff <= tolerance:
        if scaled:
            return Comparison(
                status="partially replicated",
                rationale=(
                    f"Measured {shown_measured} vs reported {shown_reported} "
                    f"in a {scale_factor * 100.0:g}%-scale run. Close, but a scaled "
                    "run cannot fully confirm or refute the paper."
                ),
                scaled=True,
                evidence_ids=evidence_ids,
            )
        return Comparison(
            status="replicated",
            rationale=f"Measured {shown_measured} vs reported {shown_reported}, within tolerance.",
            scaled=False,
            evidence_ids=evidence_ids,
        )
    if diff <= NEAR_MATCH_TOLERANCES * tolerance:
        return Comparison(
            status="partially replicated",
            rationale=(
                f"Measured {shown_measured} vs reported {shown_reported}: "
                "near match, outside tolerance."
                + (
                    " The run was scaled, so it cannot fully confirm or refute the paper."
                    if scaled
                    else ""
                )
            ),
            scaled=scaled,
            evidence_ids=evidence_ids,
        )
    if scaled:
        return Comparison(
            status="partially replicated",
            rationale=(
                f"Measured {shown_measured} vs reported {shown_reported} "
                f"in a {scale_factor * 100.0:g}%-scale run. The gap exceeds tolerance, "
                "but a scaled run cannot refute the paper."
            ),
            scaled=True,
            evidence_ids=evidence_ids,
        )
    return Comparison(
        status="not replicated",
        rationale=f"Measured {shown_measured} vs reported {shown_reported}, outside tolerance.",
        scaled=False,
        evidence_ids=evidence_ids,
    )


def compare(
    claim: Claim,
    evidence: list[Evidence],
    scale_factor: float = 1.0,
) -> Comparison:
    """Compare a measured value to a reported value (see :func:`compare_claim`)."""
    return compare_claim(claim, evidence, scale_factor)
