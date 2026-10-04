"""Verification stage: deterministic comparison (Stage 6 stub)."""

from __future__ import annotations

from collections.abc import Callable

from claimlens.claims.schema import Claim, Evidence, Plan, Verdict
from claimlens.config import RunContext


def verify_claims(
    claims: list[Claim],
    plan: Plan,
    evidence: list[Evidence],
    run: RunContext,
    runner: Callable[[Plan, RunContext], list[Evidence]] | None = None,
) -> list[Verdict]:
    """Compare measured results to reported numbers in code.

    Args:
        claims: Extracted claims under audit.
        plan: Reproduction plan (carries scale factors).
        evidence: Measured results from the sandbox.
        run: Per-run context (run_id, run_dir, config, llm).
        runner: Optional callable ``(Plan, RunContext) -> list[Evidence]``
            used for sensitivity reruns. Injected so tests can run
            without Docker.

    Returns:
        One verdict per claim. Every claim is resolved, including as
        "untestable".

    Raises:
        NotImplementedError: Stage logic is not implemented yet (Stage 6).
    """
    raise NotImplementedError
