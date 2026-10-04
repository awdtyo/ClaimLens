"""Plan stage: gap-aware reproduction plan (Stage 3 stub)."""

from __future__ import annotations

from claimlens.claims.schema import Claim, ParsedPaper, Plan
from claimlens.config import RunContext


def build_plan(parsed: ParsedPaper, claims: list[Claim], run: RunContext) -> Plan:
    """Build a reproduction plan and assumption log.

    Args:
        parsed: Output of the ingest stage.
        claims: Extracted claims to plan for.
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        Plan with per-claim items and logged assumptions.

    Raises:
        NotImplementedError: Stage logic is not implemented yet (Stage 3).
    """
    raise NotImplementedError
