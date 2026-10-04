"""Sensitivity reruns for claims that did not match (Stage 6).

For each varied assumption the stage reruns the experiment through the
injected ``runner`` — ``(Plan, RunContext) -> list[Evidence]`` — so
tests run Docker-free. Effects are ranked by absolute delta and land in
``Verdict.assumption_effects``, which the UI draws its sensitivity
chart from. Deterministic code only; no model calls here.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable

from claimlens.claims.schema import Assumption, AssumptionEffect, Claim, Evidence, Plan
from claimlens.config import RunContext

logger = logging.getLogger(__name__)

MAX_RERUNS = 3


def alternate_value(assumption: Assumption) -> str:
    """Derive a deterministic alternative for one assumption.

    Integer choices step by one (seed ``0`` -> ``1``); other numbers
    halve (noise ``0.1`` -> ``0.05``); free text gets an explicit
    ``(alternative)`` suffix. The rule is fixed so reruns are
    reproducible, not model-chosen.
    """
    chosen = assumption.value_chosen.strip()
    try:
        return str(int(chosen) + 1)
    except ValueError:
        pass
    try:
        return str(float(chosen) * 0.5)
    except ValueError:
        pass
    return f"{chosen} (alternative)"


def _base_measured(claim: Claim, evidence: list[Evidence]) -> float | None:
    for item in evidence:
        if (
            item.claim_id == claim.id
            and item.measured_value is not None
            and math.isfinite(item.measured_value)
        ):
            return item.measured_value
    return None


def run_sensitivity(
    claim: Claim,
    plan: Plan,
    evidence: list[Evidence],
    run: RunContext,
    runner: Callable[[Plan, RunContext], list[Evidence]],
    max_reruns: int = MAX_RERUNS,
) -> list[AssumptionEffect]:
    """Rerun one claim while varying each assumption once.

    Args:
        claim: Claim whose measurement did not match.
        plan: Reproduction plan carrying the assumptions.
        evidence: Main-run evidence (sets the baseline measurement).
        run: Per-run context passed through to ``runner``.
        runner: Experiment runner used for each single-assumption
            variant. Injected so tests run without Docker.
        max_reruns: Cap on reruns; the first assumptions in plan order
            are varied.

    Returns:
        AssumptionEffect records ranked by absolute delta, largest
        first. Assumptions whose rerun yields no measurement are
        skipped, never invented.
    """
    base = _base_measured(claim, evidence)
    if base is None:
        return []
    effects: list[AssumptionEffect] = []
    for assumption in plan.assumptions[:max_reruns]:
        alt = alternate_value(assumption)
        variant = plan.model_copy(deep=True)
        for candidate in variant.assumptions:
            if candidate.id == assumption.id:
                candidate.value_chosen = alt
        try:
            rerun = runner(variant, run)
        except Exception:  # noqa: BLE001 - a failed rerun skips its assumption.
            logger.debug("Sensitivity rerun for %s skipped after runner error.", assumption.id)
            continue
        measured: float | None = None
        for item in rerun or []:
            if (
                item.claim_id == claim.id
                and item.measured_value is not None
                and math.isfinite(item.measured_value)
            ):
                measured = item.measured_value
                break
        if measured is None:
            continue
        effects.append(
            AssumptionEffect(
                assumption_id=assumption.id,
                claim_id=claim.id,
                alt_value=alt,
                measured_value=measured,
                delta=measured - base,
            )
        )
    effects.sort(key=lambda effect: abs(effect.delta or 0.0), reverse=True)
    return effects


def rerun_sensitivity(
    claim: Claim,
    plan: Plan,
    evidence: list[Evidence],
    run: RunContext,
    runner: Callable[[Plan, RunContext], list[Evidence]],
    max_reruns: int = MAX_RERUNS,
) -> list[AssumptionEffect]:
    """Rerun experiments at varied scales via the injected runner."""
    return run_sensitivity(claim, plan, evidence, run, runner, max_reruns)
