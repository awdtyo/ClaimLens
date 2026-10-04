"""Sandbox stage: run experiments in Docker.

The pipeline calls :func:`run_experiments` with the blinded plan only
(``Plan.blinded`` strips reported values), so the coding agent never
sees the numbers it is trying to reproduce.
"""

from __future__ import annotations

from claimlens.claims.schema import Evidence, Plan
from claimlens.config import RunContext
from claimlens.sandbox.agent import run_agent_for_claim


def run_experiments(plan: Plan, run: RunContext) -> list[Evidence]:
    """Run planned experiments in the Docker sandbox.

    Args:
        plan: Reproduction plan with per-claim items (already blinded by
            the pipeline).
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        List of measured evidence records, one per plan item, in plan
        order. Failed items yield ``Evidence`` with ``measured_value``
        unset, never an invented number.
    """
    run.emit(
        "sandbox",
        "started",
        f"running {len(plan.items)} experiment(s)",
        {"claims": [item.claim_id for item in plan.items]},
    )
    evidence: list[Evidence] = []
    for item in plan.items:
        evidence.append(run_agent_for_claim(item.claim_id, item, run))
    run.emit(
        "sandbox",
        "done",
        f"measured {sum(1 for item in evidence if item.measured_value is not None)}/{len(evidence)} claim(s)",
        {"evidence_ids": [item.id for item in evidence]},
    )
    return evidence
