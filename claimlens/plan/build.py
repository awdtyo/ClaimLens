"""Plan stage: gap-aware reproduction plan and assumption log."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from claimlens.claims.schema import Assumption, Claim, ParsedPaper, Plan
from claimlens.config import RunContext
from claimlens.plan import gaps as gaps_mod
from claimlens.plan import spec as spec_mod

TASK = "build_plan"
MAX_ATTEMPTS = 3

PLAN_SYSTEM = (
    "Write a reduced-scale reproduction plan. Return JSON only: an object with "
    "'assumptions' and 'items'. Each assumption has 'detail' (what the paper omits), "
    "'value_chosen', 'reason' (never empty) and 'confidence' (low, medium or high). "
    "Each item has 'claim_id', 'steps', 'scale_factor' (0 < s <= 1), 'scale_reason' "
    "(why this scale) and 'config' (exact settings). Cover every claim id given."
)

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "assumptions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                    "value_chosen": {"type": "string"},
                    "reason": {"type": "string"},
                    "confidence": {"type": "string"},
                },
                "required": ["detail", "value_chosen", "reason", "confidence"],
            },
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "scale_factor": {"type": "number"},
                    "scale_reason": {"type": "string"},
                    "config": {"type": "object"},
                },
                "required": ["claim_id", "steps", "scale_factor", "config"],
            },
        },
    },
    "required": ["assumptions", "items"],
}


def plan_prompt(parsed: ParsedPaper, claims: list[Claim]) -> str:
    """Render the planner prompt from claims and deterministic gaps."""
    lines = [f"Paper: {parsed.title}", ""]
    for claim in claims:
        lines.append(
            f"Claim {claim.id} (source {claim.source_ref}): {claim.text} "
            f"[metric={claim.metric} value={claim.reported_value}]"
        )
    lines.append("")
    lines.append("Gaps found in the paper:")
    for gap in gaps_mod.find_gaps(parsed, claims):
        stated = f"stated as {gap.stated_value!r}" if gap.stated_value else "not stated"
        lines.append(f"- {gap.detail}: {stated} ({gap.context})")
    return "\n".join(lines)


def call_planner(prompt: str, run: RunContext, max_attempts: int = MAX_ATTEMPTS) -> dict[str, Any]:
    """Call the planner model until the plan validates.

    Raises:
        RuntimeError: If no gateway is attached.
        ValueError: If the output stays invalid after ``max_attempts`` tries.
    """
    gateway = run.llm
    if gateway is None or not hasattr(gateway, "complete"):
        raise RuntimeError("Plan building needs run.llm, but no gateway is attached.")
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        result = gateway.complete(  # type: ignore[union-attr]
            task=TASK,
            messages=[
                {"role": "system", "content": PLAN_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            schema=PLAN_SCHEMA,
            role="planner",
        )
        try:
            return validate_plan_result(result)
        except (ValidationError, ValueError, AttributeError, TypeError) as exc:
            last_error = exc
            run.emit(
                "plan", "progress", f"invalid plan output, retrying ({attempt}/{max_attempts})"
            )
    raise ValueError(f"Planner output stayed invalid after {max_attempts} attempts: {last_error}.")


def validate_plan_result(result: Any) -> dict[str, Any]:
    """Validate the raw planner payload (assumptions have real reasons)."""
    if not isinstance(result, dict):
        raise TypeError("Planner output is not an object.")
    raw_assumptions = result.get("assumptions", [])
    if not isinstance(raw_assumptions, list) or not raw_assumptions:
        raise ValueError("Planner output has no assumptions.")
    assumptions = []
    for item in raw_assumptions:
        if not isinstance(item, dict):
            raise TypeError("Planner assumption is not an object.")
        # Ids are assigned by build_plan; the model must not mint them.
        assumptions.append(Assumption.model_validate({**item, "id": item.get("id", "")}))
    for assumption in assumptions:
        if not assumption.reason.strip():
            raise ValueError(f"Assumption {assumption.detail!r} has an empty reason.")
    items = result.get("items", [])
    if not isinstance(items, list) or not items:
        raise ValueError("Planner output has no plan items.")
    return {"assumptions": assumptions, "items": items}


def build_plan(parsed: ParsedPaper, claims: list[Claim], run: RunContext) -> Plan:
    """Build a reproduction plan and assumption log.

    Gap analysis is deterministic; assumption values and per-claim specs
    come from the planner model with schema-constrained output. Every
    assumption is emitted as it is logged, with its reason.

    Args:
        parsed: Output of the ingest stage.
        claims: Extracted claims to plan for.
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        Plan with one item per claim and logged assumptions.
    """
    run.emit("plan", "started", f"planning {len(claims)} claims")
    validated = call_planner(plan_prompt(parsed, claims), run)
    assumptions: list[Assumption] = []
    for position, assumption in enumerate(validated["assumptions"], start=1):
        assumption.id = f"a{position}"
        assumptions.append(assumption)
        run.emit(
            "plan",
            "progress",
            f"assumption logged: {assumption.detail} = {assumption.value_chosen}",
        )
    by_claim = {claim.id: claim for claim in claims}
    items = []
    for raw in validated["items"]:
        claim_id = raw.get("claim_id") if isinstance(raw, dict) else None
        if claim_id not in by_claim:
            raise ValueError(f"Plan item targets unknown claim {claim_id!r}.")
        items.append(spec_mod.write_spec(by_claim[claim_id], raw))
    planned = {item.claim_id for item in items}
    missing = [claim.id for claim in claims if claim.id not in planned]
    if missing:
        raise ValueError(f"Planner left claims without items: {missing}.")
    run.emit("plan", "done", f"{len(items)} plan items, {len(assumptions)} assumptions")
    return Plan(items=items, assumptions=assumptions)
