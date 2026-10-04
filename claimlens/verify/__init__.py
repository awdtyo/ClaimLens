"""Verification stage: deterministic comparison (Stage 6).

Every claim is resolved, including as ``untestable``. Deterministic
code only; no model calls. Before comparing, the stage audits the
generated code: a claim with a non-advisory ``blocking`` finding gets
status ``untestable`` with a reason, never ``replicated`` — the finding
overrides even a numeric match.
"""

from __future__ import annotations

from collections.abc import Callable

from claimlens.claims.schema import Claim, CodeFinding, Evidence, Plan, Verdict
from claimlens.config import RunContext
from claimlens.verify.code_audit import audit_code
from claimlens.verify.compare import Comparison, compare_claim
from claimlens.verify.sensitivity import run_sensitivity


def _finding_claim_id(finding: CodeFinding) -> str | None:
    """Attribute a finding to a claim from its run-relative file path."""
    parts = finding.file.split("/")
    if len(parts) >= 2 and parts[0] == "code":
        return parts[1]
    return None


def apply_blocking_override(
    comparison: Comparison, findings: list[CodeFinding]
) -> tuple[str, str | None]:
    """Apply the blocking-findings rule to one claim's comparison.

    Args:
        comparison: Deterministic numeric comparison outcome.
        findings: The claim's code-audit findings.

    Returns:
        ``(status, reason)``: ``("untestable", reason)`` when a
        non-advisory ``blocking`` finding is present, otherwise the
        comparison's own status with a preserved reason.
    """
    blocking = [item for item in findings if item.severity == "blocking" and not item.advisory]
    if not blocking:
        return comparison.status, comparison.reason
    first = blocking[0]
    reason = f"Code audit blocked this claim ({first.rule}): {first.message}"
    return "untestable", reason


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
    findings = audit_code(claims, evidence, plan, run)
    by_claim: dict[str, list[CodeFinding]] = {}
    for finding in findings:
        claim_id = _finding_claim_id(finding)
        if claim_id is not None:
            by_claim.setdefault(claim_id, []).append(finding)
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
        claim_findings = by_claim.get(claim.id, [])
        status, reason = apply_blocking_override(comparison, claim_findings)
        effects = []
        if (
            status != "untestable"
            and runner is not None
            and comparison.status in ("not replicated", "partially replicated")
            and not comparison.scaled
            and plan.assumptions
        ):
            effects = run_sensitivity(claim, plan, evidence, run, runner)
        if status == "untestable" and reason:
            rationale = f"{reason} The numeric comparison is void."
        else:
            rationale = comparison.rationale
        verdicts.append(
            Verdict(
                claim_id=claim.id,
                status=status,  # type: ignore[arg-type]
                rationale=rationale,
                evidence_ids=comparison.evidence_ids,
                scaled=comparison.scaled,
                assumption_effects=effects,
                reason=reason,
                code_findings=claim_findings,
            )
        )
        run.emit(
            "verify",
            "progress",
            f"{claim.id}: {status}",
            {"claim_id": claim.id, "status": status},
        )
    run.emit(
        "verify",
        "done",
        f"resolved {len(verdicts)}/{len(claims)} claim(s)",
        {"verdicts": [verdict.status for verdict in verdicts]},
    )
    return verdicts
