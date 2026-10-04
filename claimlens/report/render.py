"""Report rendering: Markdown for humans, JSON verdicts for the UI."""

from __future__ import annotations

import json
from pathlib import Path

from claimlens.claims.schema import Assumption, Claim, Evidence, Plan, Verdict
from claimlens.config import RunContext

REPORT_MD_FILENAME = "report.md"
REPORT_JSON_FILENAME = "report.json"

SCALE_NOTE = (
    "A scaled-down run cannot refute the paper. It shows whether the "
    "result holds at a smaller scale; it does not show what a full-scale "
    "run would measure."
)


def fmt_number(value: float | None) -> str:
    """Format a normalized number for the report, or ``n/a``."""
    if value is None:
        return "n/a"
    return f"{value:g}"


def evidence_for(claim_id: str, evidence: list[Evidence]) -> list[Evidence]:
    """All evidence records measured for one claim."""
    return [item for item in evidence if item.claim_id == claim_id]


def assumption_by_id(plan: Plan, assumption_id: str) -> Assumption | None:
    """Look up a plan assumption by id."""
    for assumption in plan.assumptions:
        if assumption.id == assumption_id:
            return assumption
    return None


def render_markdown(
    claims: list[Claim],
    plan: Plan,
    evidence: list[Evidence],
    verdicts: list[Verdict],
    run_id: str,
) -> str:
    """Render the full verdict report as Markdown (pure function)."""
    by_claim = {claim.id: claim for claim in claims}
    item_by_claim = {item.claim_id: item for item in plan.items}
    lines = [
        "# ClaimLens verdict report",
        "",
        f"Run: {run_id}",
        "",
        "Values are normalized fractions (0.912 means 91.2%).",
        "",
        "## Summary",
        "",
        "| Claim | Reported | Measured | Verdict |",
        "| --- | --- | --- | --- |",
    ]
    for verdict in verdicts:
        claim = by_claim.get(verdict.claim_id)
        measured = ", ".join(
            fmt_number(item.measured_value) for item in evidence_for(verdict.claim_id, evidence)
        )
        lines.append(
            f"| {verdict.claim_id}: {(claim.text if claim else '')} "
            f"| {fmt_number(claim.reported_value) if claim else 'n/a'} "
            f"| {measured or 'n/a'} | {verdict.status} |"
        )
    lines.append("")
    for verdict in verdicts:
        claim = by_claim.get(verdict.claim_id)
        lines.append(f"## {verdict.claim_id}: {(claim.text if claim else '')}")
        lines.append("")
        lines.append(f"Verdict: {verdict.status}")
        lines.append("")
        lines.append("|  | Reported | Measured |")
        lines.append("| --- | --- | --- |")
        for item in evidence_for(verdict.claim_id, evidence):
            lines.append(
                f"| {item.id} (scale {item.scale_factor:g}) "
                f"| {fmt_number(claim.reported_value) if claim else 'n/a'} "
                f"| {fmt_number(item.measured_value)} |"
            )
        if not evidence_for(verdict.claim_id, evidence):
            lines.append(
                f"| no measurement | {fmt_number(claim.reported_value) if claim else 'n/a'} | n/a |"
            )
        lines.append("")
        lines.append(verdict.rationale)
        lines.append("")
        if verdict.assumption_effects:
            lines.append("Assumptions that mattered most (sensitivity reruns):")
            lines.append("")
            for effect in verdict.assumption_effects:
                assumption = assumption_by_id(plan, effect.assumption_id)
                detail = assumption.detail if assumption else effect.assumption_id
                lines.append(
                    f"- {detail}: tried {effect.alt_value}, measured "
                    f"{fmt_number(effect.measured_value)} "
                    f"(delta {fmt_number(effect.delta)})."
                )
            lines.append("")
        item = item_by_claim.get(verdict.claim_id)
        if verdict.scaled or (item is not None and item.scale_factor < 1.0):
            lines.append("Scale limitation:")
            lines.append("")
            if item is not None and item.scale_reason:
                lines.append(item.scale_reason)
            lines.append(SCALE_NOTE)
            lines.append("")
        logs = [item.logs_ref for item in evidence_for(verdict.claim_id, evidence) if item.logs_ref]
        if logs:
            lines.append("Logs:")
            lines.append("")
            for ref in logs:
                lines.append(f"- {ref}")
            lines.append("")
    if plan.assumptions:
        lines.append("## Assumptions")
        lines.append("")
        for assumption in plan.assumptions:
            lines.append(
                f"- {assumption.id}: {assumption.detail} = {assumption.value_chosen} "
                f"(confidence {assumption.confidence}). {assumption.reason}"
            )
        lines.append("")
    lines.append("## Run logs")
    lines.append("")
    lines.append("- llm_log.jsonl: per-call model usage for this run.")
    lines.append("- events.jsonl: live progress events for this run.")
    lines.append("")
    return "\n".join(lines)


def render_report(
    claims: list[Claim],
    plan: Plan,
    evidence: list[Evidence],
    verdicts: list[Verdict],
    run: RunContext,
) -> Path:
    """Write the verdict report (Markdown plus Verdict-schema JSON).

    Writes ``report.md`` for readers and ``report.json`` holding the
    verdict list unchanged for the UI, and returns the Markdown path.
    The pipeline records that path in ``07_report.json``.

    Args:
        claims: Extracted claims under audit.
        plan: Reproduction plan (carries assumptions).
        evidence: Measured results from the sandbox.
        verdicts: Verification outcomes, one per claim.
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        Path to the rendered ``report.md`` file.
    """
    run.emit("report", "started", f"rendering report for {len(verdicts)} verdicts")
    run_dir = Path(run.run_dir)  # type: ignore[arg-type]
    run_dir.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(claims, plan, evidence, verdicts, run.run_id)
    md_path = run_dir / REPORT_MD_FILENAME
    md_path.write_text(markdown, encoding="utf-8")
    run.emit("report", "progress", f"wrote {REPORT_MD_FILENAME}")
    json_path = run_dir / REPORT_JSON_FILENAME
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump([verdict.model_dump(mode="json") for verdict in verdicts], handle, indent=2)
        handle.write("\n")
    run.emit("report", "progress", f"wrote {REPORT_JSON_FILENAME}")
    run.emit("report", "done", f"report written to {md_path.name}")
    return md_path
