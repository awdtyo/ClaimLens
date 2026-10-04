"""Code audit stage: check generated experiment code before the verdict.

STUB — owned by Part C per AGENTS.md ownership; added here as an
explicitly requested contract seam. Deterministic checks may mark a run
invalid (a claim with a non-advisory blocking finding gets verdict
``untestable`` with a reason, never ``replicated``); LLM review is
advisory only and never changes a verdict.
"""

from __future__ import annotations

from claimlens.claims.schema import Claim, CodeFinding, Evidence, Plan
from claimlens.config import RunContext


def audit_code(
    claims: list[Claim],
    evidence: list[Evidence],
    plan: Plan,
    run: RunContext,
) -> list[CodeFinding]:
    """Audit generated code under ``runs/<run_id>/code/<claim_id>/iter_<n>/``.

    Args:
        claims: Extracted claims under audit.
        evidence: Measured results (carry ``code_dir`` and ``iterations``).
        plan: Reproduction plan (the unblinded original).
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        Findings, one per broken rule. Deterministic findings carry
        ``advisory=False``; LLM review findings carry ``advisory=True``.

    Raises:
        NotImplementedError: Stage logic is not implemented yet (Part C).
    """
    raise NotImplementedError
