"""Pydantic data models for ClaimLens.

All stages exchange these models. They are the stable contract between
team parts; changes need an issue and admin approval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


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


class Evidence(BaseModel):
    """A measured result from a sandbox experiment."""

    id: str
    claim_id: str
    method: str
    measured_value: float | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    logs_ref: str | None = None
    scale_factor: float = 1.0


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
