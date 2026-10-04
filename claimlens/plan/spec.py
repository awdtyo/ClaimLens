"""Reproduction spec writing: one reduced-scale item per claim."""

from __future__ import annotations

from typing import Any

from claimlens.claims.schema import Claim, PlanItem

DEFAULT_SCALE_REASON = (
    "Reduced scale keeps the reproduction cheap; a scaled run cannot refute the paper."
)


def write_spec(claim: Claim, spec: dict[str, Any]) -> PlanItem:
    """Validate one raw spec dict into a PlanItem for the claim.

    Fills in a default scale reason when the model gives none, so the
    report can always state what the scaled run does and does not show.

    Raises:
        ValueError: If the spec targets another claim, has no steps, or
            has an out-of-range scale factor.
    """
    if spec.get("claim_id", claim.id) != claim.id:
        raise ValueError(f"Spec targets {spec.get('claim_id')!r}, expected {claim.id!r}.")
    steps = spec.get("steps", [])
    if not steps:
        raise ValueError(f"Spec for claim {claim.id} has no steps.")
    try:
        scale_factor = float(spec.get("scale_factor", 1.0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Spec for claim {claim.id} has a bad scale_factor.") from exc
    if not 0.0 < scale_factor <= 1.0:
        raise ValueError(f"Spec for claim {claim.id} has scale_factor {scale_factor}.")
    config = spec.get("config", {})
    if not isinstance(config, dict):
        raise TypeError(f"Spec for claim {claim.id} has a non-object config.")
    scale_reason = str(spec.get("scale_reason", "") or "").strip() or DEFAULT_SCALE_REASON
    return PlanItem(
        claim_id=claim.id,
        steps=[str(step) for step in steps],
        scale_factor=scale_factor,
        scale_reason=scale_reason,
        config={str(key): value for key, value in config.items()},
    )
