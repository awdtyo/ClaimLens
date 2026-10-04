"""Claim extraction stage (Stage 2 stub)."""

from __future__ import annotations

from claimlens.claims.schema import Claim, ParsedPaper
from claimlens.config import RunContext


def extract_claims(parsed: ParsedPaper, run: RunContext) -> list[Claim]:
    """Extract testable claims from a parsed paper.

    Args:
        parsed: Output of the ingest stage.
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        List of claims, each with a real source_ref.

    Raises:
        NotImplementedError: Stage logic is not implemented yet (Stage 2).
    """
    raise NotImplementedError
