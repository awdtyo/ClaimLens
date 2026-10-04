"""Verification stage: deterministic comparison (Stage 6).

Every claim is resolved, including as ``untestable``. Deterministic
code only; no model calls.
"""

from __future__ import annotations

from collections.abc import Callable

from claimlens.claims.schema import Claim, Evidence, Plan, Verdict
from claimlens.config import RunContext
from claimlens.verify.compare import compare_claim
from claimlens.verify.sensitivity import run_sensitivity


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
    """
    run.emit(
        "verify",
        "started",
        f"verifying {len(claims)} claim(s)",
        {"claims": [claim.id for claim in claims]},
    )
    scale_by_claim = {item.claim_id: item.scale_factor for item in plan.items}
    verdicts: list[Verdict] = []
    for claim in claims:
        run.emit("verify", "progress", f"{claim.id}: comparing", {"claim_id": claim.id})
        comparison = compare_claim(claim, evidence, scale_by_claim.get(claim.id, 1.0))
        effects = []
        if (
            runner is not None
            and comparison.status in ("not replicated", "partially replicated")
            and not comparison.scaled
            and plan.assumptions
        ):
            effects = run_sensitivity(claim, plan, evidence, run, runner)
        verdicts.append(
            Verdict(
                claim_id=claim.id,
                status=comparison.status,  # type: ignore[arg-type]
                rationale=comparison.rationale,
                evidence_ids=comparison.evidence_ids,
                scaled=comparison.scaled,
                assumption_effects=effects,
                reason=comparison.reason,
                code_findings=[],
            )
        )
        run.emit(
            "verify",
            "progress",
            f"{claim.id}: {comparison.status}",
            {"claim_id": claim.id, "status": comparison.status},
        )
    run.emit(
        "verify",
        "done",
        f"resolved {len(verdicts)}/{len(claims)} claim(s)",
        {"verdicts": [verdict.status for verdict in verdicts]},
    )
    return verdicts
