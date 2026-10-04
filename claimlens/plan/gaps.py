"""Gap analysis: details the paper states, omits, or leaves to the agent."""

from __future__ import annotations

import re
from dataclasses import dataclass

from claimlens.claims.schema import Claim, ParsedPaper

# (detail, pattern, group) tried against the method/experiment text.
SETTING_PATTERNS: tuple[tuple[str, str], ...] = (
    ("random seed", r"seed(?:s)?(?: of | is |: |=)\s*(\d+)"),
    ("learning rate", r"learning rate(?: of | is |: |=)\s*([\d.]+)"),
    ("batch size", r"batch size(?: of | is |: |=)\s*(\d+)"),
    ("training epochs", r"(\d+)\s*epochs"),
    ("train/test split sizes", r"(\d+)\s*training and (\d+)\s*test"),
    ("evaluation metric", r"(accuracy|error rate|f1|auc)"),
)

# Details a scaled reproduction always needs, whatever the paper states.
SCALE_GAPS: tuple[tuple[str, str], ...] = (
    (
        "training data subsample for the scaled run",
        "Reduced-scale runs train on a fraction of the data; the paper never defines which fraction.",
    ),
)


@dataclass(frozen=True)
class Gap:
    """One reproduction detail with what the paper says about it."""

    detail: str
    stated_value: str | None
    context: str


def method_text(parsed: ParsedPaper) -> str:
    """Text of the method/experiment sections, where settings live."""
    texts = []
    for section in parsed.sections:
        if section.title.lower() in ("method", "methods", "experiments", "experimental setup"):
            texts.append(section.text)
    return " ".join(texts) if texts else " ".join(section.text for section in parsed.sections)


def extract_stated_settings(parsed: ParsedPaper) -> dict[str, str]:
    """Settings the paper states explicitly (detail -> value)."""
    text = method_text(parsed).lower()
    stated = {}
    for detail, pattern in SETTING_PATTERNS:
        match = re.search(pattern, text)
        if match:
            stated[detail] = match.group(0)
    return stated


def find_gaps(parsed: ParsedPaper, claims: list[Claim]) -> list[Gap]:
    """List reproduction details the paper omits or leaves to the agent.

    Covers each testable claim: stated settings are reported with their
    value (the plan still pins them down), unstated standard settings
    and the scaled-run subsample are reported without one.
    """
    testable = [claim for claim in claims if claim.testable]
    stated = extract_stated_settings(parsed)
    gaps = [
        Gap(
            detail=detail,
            stated_value=stated.get(detail),
            context=f"reproducing {claim.id}: {claim.text}",
        )
        for claim in testable
        for detail in ("random seed", "learning rate", "batch size", "training epochs")
    ]
    for detail, context in SCALE_GAPS:
        gaps.append(Gap(detail=detail, stated_value=None, context=context))
    return gaps
