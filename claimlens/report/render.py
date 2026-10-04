"""Report rendering stage (Stage 7 stub)."""

from __future__ import annotations

from pathlib import Path

from claimlens.claims.schema import Claim, Evidence, Plan, Verdict
from claimlens.config import RunContext


def render_report(
    claims: list[Claim],
    plan: Plan,
    evidence: list[Evidence],
    verdicts: list[Verdict],
    run: RunContext,
) -> Path:
    """Write a per-claim verdict report.

    Args:
        claims: Extracted claims under audit.
        plan: Reproduction plan (carries assumptions).
        evidence: Measured results from the sandbox.
        verdicts: Verification outcomes, one per claim.
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        Path to the rendered report file.

    Raises:
        NotImplementedError: Stage logic is not implemented yet (Stage 7).
    """
    raise NotImplementedError
