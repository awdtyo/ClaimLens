"""Sandbox stage: run experiments in Docker (Stages 4-5 stub)."""

from __future__ import annotations

from claimlens.claims.schema import Evidence, Plan
from claimlens.config import RunContext


def run_experiments(plan: Plan, run: RunContext) -> list[Evidence]:
    """Run planned experiments in the Docker sandbox.

    Args:
        plan: Reproduction plan with per-claim items.
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        List of measured evidence records, one or more per claim.

    Raises:
        NotImplementedError: Stage logic is not implemented yet (Stage 4/5).
    """
    raise NotImplementedError
