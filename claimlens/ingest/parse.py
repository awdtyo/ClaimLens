"""Ingest stage: parse a paper PDF into structured content."""

from __future__ import annotations

from pathlib import Path

from claimlens.claims.schema import ParsedPaper
from claimlens.config import RunContext
from claimlens.ingest import pdf_text, tables


def parse_paper(pdf_path: Path, run: RunContext) -> ParsedPaper:
    """Parse a paper PDF into sections, tables and cross-check mismatches.

    Text-layer tables and page-image (vision) tables are extracted
    separately and compared cell by cell; every difference is recorded
    in ``table_mismatches`` and both readings are kept. Progress is
    emitted per page, section, table and mismatch for the web UI.

    Args:
        pdf_path: Path to the paper PDF.
        run: Per-run context (run_id, run_dir, config, llm).

    Returns:
        ParsedPaper with title, sections, tables and table_mismatches.
    """
    path = Path(pdf_path)
    run.emit("ingest", "started", f"parsing {path.name}")
    doc = pdf_text.extract_pages(path)
    for page in doc.pages:
        run.emit("ingest", "progress", f"page parsed: {page.page}")
    sections = pdf_text.split_sections(doc)
    for section in sections:
        run.emit("ingest", "progress", f"section parsed: {section.title} (page {section.page})")
    text_tables = tables.extract_text_tables(doc.pages, pdf_path=path)
    for table in text_tables:
        run.emit("ingest", "progress", f"table extracted: {table.id} (page {table.page})")
    # The vision pass only covers pages with a caption or a text-layer
    # table, to save model quota; other pages are text-only.
    vision_pages = tables.pages_with_tables(doc.pages, text_tables)
    pages_png = [(number, tables.render_page_png(path, number)) for number in vision_pages]
    vision_raw = tables.read_vision_tables(pages_png, run)
    for entry in vision_raw:
        run.emit("ingest", "progress", f"vision table read (page {entry.page})")
    vision_tables, mismatches = tables.pair_and_compare(text_tables, vision_raw)
    for mismatch in mismatches:
        run.emit(
            "ingest",
            "progress",
            f"mismatch found: {mismatch.table_id} row {mismatch.row} col {mismatch.col}",
        )
    run.emit(
        "ingest",
        "done",
        f"{len(sections)} sections, {len(text_tables)} tables, {len(mismatches)} mismatches",
    )
    return ParsedPaper(
        title=doc.title,
        sections=sections,
        tables=[*text_tables, *vision_tables],
        table_mismatches=mismatches,
    )
