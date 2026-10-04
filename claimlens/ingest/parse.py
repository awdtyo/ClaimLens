"""Ingest stage: parse a paper PDF into structured content."""

from __future__ import annotations

from pathlib import Path

from claimlens.claims.schema import ParsedPaper
from claimlens.config import RunContext


def parse_paper(pdf_path: Path, run: RunContext) -> ParsedPaper:
    """Parse a paper PDF into sections, tables and cross-check mismatches.

    Args:
        pdf_path: Path to the paper PDF.
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        ParsedPaper with title, sections, tables and table_mismatches.

    Raises:
        NotImplementedError: Stage logic is not implemented yet (Stage 1).
    """
    raise NotImplementedError
