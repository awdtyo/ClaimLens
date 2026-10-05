"""Advisory LLM review of generated experiment code.

Uses the model gateway (``task="code_review"``) to check whether the
code implements the method described in the plan. Every finding carries
``advisory=True`` and never changes a verdict — deterministic checks in
:mod:`claimlens.verify.code_audit` decide validity. Invalid model
output yields no findings, never a crash.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from claimlens.claims.schema import Claim, CodeFinding, Evidence, Plan
from claimlens.config import RunContext
from claimlens.verify.code_audit import collect_claim_code

logger = logging.getLogger(__name__)

MAX_FINDINGS_PER_CLAIM = 10
MAX_CODE_CHARS = 6000

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule": {"type": "string"},
                    "severity": {"type": "string"},
                    "file": {"type": "string"},
                    "line": {"type": ["integer", "null"]},
                    "message": {"type": "string"},
                },
                "required": ["rule", "message"],
            },
        }
    },
    "required": ["findings"],
}

SYSTEM_PROMPT = (
    "You review experiment code for a paper reproduction. "
    "Given the plan steps and the generated files, list findings as JSON "
    '{"findings": [{"rule": ..., "severity": "warning"|"info", '
    '"file": ..., "line": ...|null, "message": ...}]}. '
    "Flag only concrete gaps between the plan and the code "
    "(missing steps, wrong data, unset seeds). "
    "Reply with an empty findings list when the code follows the plan."
)


def _coerce_findings(response: Any, known_files: list[str]) -> list[CodeFinding]:
    """Validate model output into advisory findings; garbage yields none."""
    if not isinstance(response, dict):
        return []
    raw = response.get("findings")
    if not isinstance(raw, list):
        return []
    findings: list[CodeFinding] = []
    for entry in raw[:MAX_FINDINGS_PER_CLAIM]:
        if not isinstance(entry, dict):
            continue
        rule = entry.get("rule")
        message = entry.get("message")
        if not isinstance(rule, str) or not rule.strip():
            continue
        if not isinstance(message, str) or not message.strip():
            continue
        claimed_file = entry.get("file")
        file = (
            claimed_file
            if isinstance(claimed_file, str) and claimed_file in known_files
            else (known_files[0] if known_files else "")
        )
        if not file:
            continue
        line = entry.get("line")
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            line = None
        severity = entry.get("severity")
        severity = severity if severity in ("warning", "info") else "warning"
        findings.append(
            CodeFinding(
                rule=f"review-{rule.strip()}",
                severity=severity,  # type: ignore[arg-type]
                file=file,
                line=line,
                message=message.strip(),
                advisory=True,
            )
        )
    return findings


def review_code(
    claims: list[Claim],
    evidence: list[Evidence],
    plan: Plan,
    run: RunContext,
) -> list[CodeFinding]:
    """Review generated code with the model; findings are advisory only.

    Args:
        claims: Extracted claims under audit.
        evidence: Measured results (carry ``code_dir`` and ``iterations``).
        plan: Reproduction plan (steps are blinded before prompting, so
            reported values never reach the reviewer).
        run: Per-run context (provides the model gateway).

    Returns:
        Advisory findings (``advisory=True``). Invalid model output or a
        missing gateway yields no findings instead of an error.
    """
    gateway = run.llm
    if gateway is None:
        return []
    run_dir = Path(run.run_dir)  # type: ignore[arg-type]
    blinded = plan.blinded(claims)
    blinded_steps = {item.claim_id: item.steps for item in blinded.items}
    findings: list[CodeFinding] = []
    for claim in claims:
        code = collect_claim_code(run_dir, claim.id, evidence)
        if not code.python_files:
            continue
        excerpt = "\n\n".join(
            f"--- {item.rel} ---\n{item.text[:MAX_CODE_CHARS]}" for item in code.python_files
        )[:MAX_CODE_CHARS]
        steps = blinded_steps.get(claim.id, [])
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Plan steps:\n"
                + "\n".join(f"- {step}" for step in steps)
                + "\n\nGenerated code:\n"
                + excerpt,
            },
        ]
        try:
            response = gateway.complete(  # type: ignore[union-attr]
                task="code_review",
                messages=messages,
                schema=REVIEW_SCHEMA,
                role="agent",
            )
        except Exception as e:  # noqa: BLE001 - review must never break the pipeline.
            logger.debug("Code review for %s failed: %s", claim.id, e)
            continue
        known = [item.rel for item in code.files]
        findings.extend(_coerce_findings(response, known))
    return findings
