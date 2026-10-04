"""Pydantic data models for ClaimLens.

All stages exchange these models. They are the stable contract between
team parts; changes need an issue and admin approval.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

REDACTED = "[redacted]"


class Claim(BaseModel):
    """A single testable claim extracted from a paper.

    ``reported_value`` is normalized to unit-free numbers: percentages
    and percentage points become fractions (91.2% -> 0.912).
    ``tolerance`` uses the same units. ``source_ref`` is a section or
    table id from the parsed paper.
    """

    id: str
    text: str
    source_ref: str
    metric: str | None = None
    dataset: str | None = None
    baseline: str | None = None
    reported_value: float | None = None
    tolerance: float | None = None
    testable: bool = True
    page: int | None = None


class Assumption(BaseModel):
    """A detail the paper omits that the agent fills in."""

    id: str
    detail: str
    value_chosen: str
    reason: str
    confidence: Literal["low", "medium", "high"]


class AssumptionEffect(BaseModel):
    """How one assumption changes a measured result.

    Records a sensitivity rerun where a single assumption was varied:
    the alternative value tried, the measured value under it, and the
    delta versus the main measurement.
    """

    assumption_id: str
    claim_id: str
    alt_value: str
    measured_value: float | None = None
    delta: float | None = None


class CodeFinding(BaseModel):
    """One code-audit finding on generated experiment code.

    Deterministic checks (``advisory=False``) may mark a run invalid: a
    claim with a non-advisory ``blocking`` finding gets verdict
    ``untestable`` with a reason, never ``replicated``. LLM review
    findings are ``advisory=True`` and never change a verdict.
    """

    rule: str
    severity: Literal["blocking", "warning", "info"]
    file: str
    line: int | None = None
    message: str
    advisory: bool = True


class Evidence(BaseModel):
    """A measured result from a sandbox experiment."""

    id: str
    claim_id: str
    method: str
    measured_value: float | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    logs_ref: str | None = None
    scale_factor: float = 1.0
    code_dir: str | None = None
    iterations: int = 0


class Verdict(BaseModel):
    """The verification outcome for one claim."""

    claim_id: str
    status: Literal[
        "replicated",
        "partially replicated",
        "not replicated",
        "untestable",
        "untestable at this scale",
    ]
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    scaled: bool = False
    assumption_effects: list[AssumptionEffect] = Field(default_factory=list)
    reason: str | None = None
    code_findings: list[CodeFinding] = Field(default_factory=list)


class Section(BaseModel):
    """One paper section."""

    id: str
    title: str
    text: str
    page: int | None = None


class Table(BaseModel):
    """A results table read from one source."""

    id: str
    caption: str = ""
    rows: list[list[str]] = Field(default_factory=list)
    source: Literal["text", "vision"]
    page: int | None = None


class TableMismatch(BaseModel):
    """A cell where the text layer and vision read disagree."""

    table_id: str
    row: int
    col: int
    text_value: str
    vision_value: str


class ParsedPaper(BaseModel):
    """Output of the ingest stage."""

    title: str
    sections: list[Section] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    table_mismatches: list[TableMismatch] = Field(default_factory=list)


class PlanItem(BaseModel):
    """Reproduction steps for one claim."""

    claim_id: str
    steps: list[str] = Field(default_factory=list)
    scale_factor: float = 1.0
    scale_reason: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """Output of the plan stage."""

    items: list[PlanItem] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)

    def blinded(self, claims: Iterable[Claim] = ()) -> Plan:
        """Return a copy with every reported value removed.

        The coding agent never receives reported values: string
        occurrences of each claim's ``reported_value`` (unit-free and
        percent forms, e.g. ``0.912`` and ``91.2``) are replaced with
        ``[redacted]`` in steps, scale reasons, string config values
        and assumption text. Numeric config settings (hyperparameters
        such as epochs or seeds) are preserved untouched. The original
        plan is not modified.

        Known limit: integral reported values with no fractional surface
        form (e.g. a bare count ``12``) are left in place, since blind
        string matching would also destroy ordinary integers the agent
        needs.
        """
        redacted = self.model_copy(deep=True)
        variants: set[str] = set()
        for claim in claims:
            variants.update(_reported_variants(claim.reported_value))
        if not variants:
            return redacted
        for item in redacted.items:
            item.steps = [_redact_text(step, variants) for step in item.steps]
            item.scale_reason = _redact_text(item.scale_reason, variants)
            item.config = _redact_value(item.config, variants)
        for assumption in redacted.assumptions:
            assumption.detail = _redact_text(assumption.detail, variants)
            assumption.value_chosen = _redact_text(assumption.value_chosen, variants)
            assumption.reason = _redact_text(assumption.reason, variants)
        return redacted


def _reported_variants(value: float | None) -> set[str]:
    """String forms under which a normalized reported value may appear."""
    if value is None:
        return set()
    variants: set[str] = set()
    plain = f"{value:g}"
    if "." in plain or "e" in plain.lower():
        variants.add(plain)
        variants.add(f"{value * 100.0:g}")
    return variants


def _redact_text(text: str, variants: set[str]) -> str:
    """Replace every reported-value occurrence with ``[redacted]``."""
    for variant in sorted(variants, key=len, reverse=True):
        text = text.replace(variant, REDACTED)
    return text


def _redact_value(value: Any, variants: set[str]) -> Any:
    """Redact reported values inside JSON-like config structures.

    Only string content is touched; numbers, booleans and nulls pass
    through so hyperparameters survive blinding.
    """
    if isinstance(value, str):
        return _redact_text(value, variants)
    if isinstance(value, list):
        return [_redact_value(item, variants) for item in value]
    if isinstance(value, dict):
        return {key: _redact_value(item, variants) for key, item in value.items()}
    return value


class RunContext(BaseModel):
    """Per-run context injected into every stage.

    Note: claimlens.config.RunContext is the runtime (non-serialised)
    variant. This model exists so RunContext can appear in artifact
    payloads if needed. Stages should import RunContext from
    claimlens.config.
    """

    model_config = {"arbitrary_types_allowed": True}

    run_id: str
    run_dir: Path
    config: dict[str, Any] = Field(default_factory=dict)
    llm: Any = None
