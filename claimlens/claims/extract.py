"""Claim extraction stage: testable claims with normalized numbers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from claimlens.claims.schema import Claim, ParsedPaper
from claimlens.config import RunContext

TASK = "extract_claims"
MAX_ATTEMPTS = 3
DEFAULT_TOLERANCE = 0.01

EXTRACT_SYSTEM = (
    "Extract every testable empirical claim from the paper excerpt. Return JSON only: "
    "an object with a 'claims' list. Each claim has 'text' (the claim sentence), "
    "'metric' (e.g. accuracy), 'dataset' (e.g. D, null when none), 'baseline' "
    "(comparison method, null when none), 'reported_value' (the number as stated), "
    "'reported_unit' ('percent', 'percentage_points', 'ratio' or 'count'), "
    "'tolerance' (comparison tolerance in reported units, null for default), "
    "'source_ref' (the section or table id the claim comes from, e.g. 't1'), "
    "and 'testable' (false when the claim has no measurable number)."
)

DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "metric": {"type": "string"},
                    "dataset": {"type": "string"},
                    "baseline": {"type": "string"},
                    "reported_value": {},
                    "reported_unit": {"type": "string"},
                    "tolerance": {},
                    "source_ref": {"type": "string"},
                    "testable": {"type": "boolean"},
                },
                "required": ["text", "source_ref"],
            },
        }
    },
    "required": ["claims"],
}


class ClaimDraft(BaseModel):
    """One raw model-proposed claim, validated before normalization."""

    text: str
    metric: str | None = None
    dataset: str | None = None
    baseline: str | None = None
    reported_value: float | str | None = None
    reported_unit: str | None = None
    tolerance: float | None = None
    source_ref: str
    page: int | None = None
    testable: bool = True


def normalize_value(value: float | str | None, unit: str | None) -> float | None:
    """Normalize a reported number to unit-free form.

    Percentages and percentage points become fractions (``91.2%`` ->
    0.912). Ratios and counts pass through unchanged.
    """
    if value is None:
        return None
    text = str(value).strip().rstrip("%").strip()
    try:
        number = float(text)
    except ValueError:
        return None
    if str(value).strip().endswith("%") or (unit or "").strip().lower() in (
        "percent",
        "percentage_points",
        "percentage-point",
        "pp",
    ):
        return number / 100.0
    return number


def normalize_tolerance(tolerance: float | None) -> float:
    """Return a positive tolerance in normalized units (default 0.01)."""
    if tolerance is None or tolerance <= 0:
        return DEFAULT_TOLERANCE
    return tolerance


def paper_text(parsed: ParsedPaper) -> str:
    """Render the parsed paper as plain text for the extraction prompt."""
    parts = [f"Title: {parsed.title}"]
    for section in parsed.sections:
        parts.append(f"[Section {section.id}: {section.title}] {section.text}")
    for table in parsed.tables:
        if table.source != "text":
            continue
        rows = "; ".join(" | ".join(row) for row in table.rows)
        parts.append(f"[Table {table.id}: {table.caption}] {rows}")
    return "\n\n".join(parts)


def valid_source_ids(parsed: ParsedPaper) -> set[str]:
    """Section and table ids that claims may reference."""
    return {section.id for section in parsed.sections} | {table.id for table in parsed.tables}


def source_page(parsed: ParsedPaper, source_ref: str) -> int | None:
    """Authoritative page for a section or table id."""
    for section in parsed.sections:
        if section.id == source_ref:
            return section.page
    for table in parsed.tables:
        if table.id == source_ref:
            return table.page
    return None


def draft_to_claim(draft: ClaimDraft, claim_id: str, parsed: ParsedPaper) -> Claim:
    """Normalize one validated draft into a Claim."""
    return Claim(
        id=claim_id,
        text=draft.text.strip(),
        source_ref=draft.source_ref,
        metric=draft.metric,
        dataset=draft.dataset,
        baseline=draft.baseline,
        reported_value=normalize_value(draft.reported_value, draft.reported_unit),
        tolerance=normalize_tolerance(draft.tolerance),
        testable=draft.testable,
        page=source_page(parsed, draft.source_ref) or draft.page,
    )


def call_model_drafts(
    prompt: str, run: RunContext, label: str, max_attempts: int = MAX_ATTEMPTS
) -> list[ClaimDraft]:
    """Call the model until its output validates, then return drafts.

    Raises:
        RuntimeError: If no gateway is attached.
        ValueError: If the output stays invalid after ``max_attempts`` tries.
    """
    gateway = run.llm
    if gateway is None or not hasattr(gateway, "complete"):
        raise RuntimeError("Claim extraction needs run.llm, but no gateway is attached.")
    last_error: ValidationError | ValueError | None = None
    for attempt in range(1, max_attempts + 1):
        result = gateway.complete(  # type: ignore[union-attr]
            task=TASK,
            messages=[
                {"role": "system", "content": EXTRACT_SYSTEM},
                {"role": "user", "content": f"{label}\n\n{prompt}"},
            ],
            schema=DRAFT_SCHEMA,
            role="agent",
        )
        try:
            items = result.get("claims", []) if isinstance(result, dict) else []
            drafts = [ClaimDraft.model_validate(item) for item in items]
            if not drafts:
                raise ValueError("Model returned no claims.")
            return drafts
        except (ValidationError, ValueError, AttributeError) as exc:
            last_error = exc
            run.emit(
                "claims", "progress", f"invalid model output, retrying ({attempt}/{max_attempts})"
            )
    raise ValueError(f"Model output stayed invalid after {max_attempts} attempts: {last_error}.")


def chunk_prompts(parsed: ParsedPaper, run: RunContext) -> list[str]:
    """One prompt per paper, or one per section when over context budget."""
    from claimlens.llm import approx_tokens

    max_context = run.config.max_context if run.config else 30000
    full = paper_text(parsed)
    if approx_tokens(full) <= max_context:
        return [full]
    chunks = []
    for section in parsed.sections:
        tables = " ".join(
            " | ".join(cell for row in table.rows for cell in row)
            for table in parsed.tables
            if table.source == "text"
        )
        chunks.append(f"[Section {section.id}: {section.title}] {section.text}\nTables: {tables}")
    return chunks


def extract_claims(parsed: ParsedPaper, run: RunContext) -> list[Claim]:
    """Extract testable claims from a parsed paper.

    Numbers are normalized in Python (91.2% -> 0.912); the model never
    decides the comparison values. Claims whose ``source_ref`` is not a
    real section or table id are rejected. Progress is emitted per
    extracted claim, rejected reference and retry.

    Args:
        parsed: Output of the ingest stage.
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        List of claims with ids ``c1``, ``c2``, ... in paper order.
    """
    run.emit("claims", "started", "extracting claims")
    known_ids = valid_source_ids(parsed)
    seen_texts: set[str] = set()
    drafts: list[ClaimDraft] = []
    prompts = chunk_prompts(parsed, run)
    for index, prompt in enumerate(prompts, start=1):
        label = (
            f"Paper: {parsed.title}"
            if len(prompts) == 1
            else f"Paper section {index}/{len(prompts)}"
        )
        for draft in call_model_drafts(prompt, run, label):
            key = draft.text.strip().lower()
            if key in seen_texts:
                continue  # same claim found in another chunk
            seen_texts.add(key)
            drafts.append(draft)
    claims: list[Claim] = []
    for position, draft in enumerate(drafts, start=1):
        if draft.source_ref not in known_ids:
            run.emit(
                "claims", "progress", f"claim rejected: unknown source_ref {draft.source_ref!r}"
            )
            continue
        claim = draft_to_claim(draft, f"c{position}", parsed)
        if claim.page is None:
            run.emit("claims", "progress", f"claim extracted without page: {claim.id}")
        else:
            run.emit(
                "claims", "progress", f"claim extracted: {claim.id} (source {claim.source_ref})"
            )
        claims.append(claim)
    # Renumber after rejections so ids stay dense.
    for position, claim in enumerate(claims, start=1):
        claim.id = f"c{position}"
    run.emit("claims", "done", f"{len(claims)} claims extracted")
    return claims
