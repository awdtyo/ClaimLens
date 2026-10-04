"""Table extraction from the text layer and page images, with cross-check.

Text-layer tables come from PyMuPDF's table finder with a fallback to
``|``-delimited lines (used by the generated fixture PDFs). Vision
tables come from page renders transcribed by Gemma 4 through
``claimlens/llm.py`` (task ``"table_vision"``). The two readings are
paired by page and order; every differing cell becomes a
``TableMismatch``. Both readings are kept — neither is picked silently.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf

from claimlens.claims.schema import Table, TableMismatch
from claimlens.config import RunContext
from claimlens.ingest.pdf_text import CAPTION_RE, PageLines

logger = logging.getLogger(__name__)

TABLE_TASK = "table_vision"

CAPTION_PREFIX_RE = re.compile(r"^Table\s+\d+\s*:\s*(.*)$")

VISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "caption": {"type": "string"},
                    "rows": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "required": ["rows"],
            },
        }
    },
    "required": ["tables"],
}

VISION_SYSTEM = (
    "Transcribe every results table visible in the paper page image. "
    "Return JSON only: an object with a 'tables' list. Each table has "
    "'caption' (empty string when none is visible) and 'rows' (list of "
    "lists of cell strings, header row first). Transcribe what you see; "
    "do not invent values."
)


@dataclass(frozen=True)
class VisionTable:
    """One table transcribed from a page image (id assigned on pairing)."""

    page: int
    caption: str
    rows: list[list[str]] = field(default_factory=list)


def parse_pipe_row(line: str) -> list[str] | None:
    """Parse one ``| a | b |`` line into cells.

    Returns None for separator rows (``|---|---|``) and non-table lines.
    """
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if cells and all(set(cell) <= set("-: ") for cell in cells):
        return None
    return cells


def _find_tables_find_tables(page: pymupdf.Page) -> list[list[list[str]]]:
    """Extract tables with PyMuPDF's table finder. Returns row grids."""
    grids: list[list[list[str]]] = []
    try:
        found = page.find_tables()
    except Exception as exc:  # noqa: BLE001 - finder is best-effort; pipe fallback covers fixtures
        logger.debug("table finder failed: %s", exc)
        return grids
    for table in found:
        try:
            rows = table.extract()
        except Exception as exc:  # noqa: BLE001 - skip one unreadable table, keep the rest
            logger.debug("skipping unreadable table: %s", exc)
            continue
        grids.append([[str(cell or "").strip() for cell in row] for row in rows])
    return grids


def extract_text_tables(pages: list[PageLines], pdf_path: Path | str | None = None) -> list[Table]:
    """Extract text-layer tables, in document order, as ``t1``, ``t2``, ....

    Uses PyMuPDF's table finder when ``pdf_path`` is given, with a
    fallback to ``|``-delimited lines. Captions come from the nearest
    preceding ``Table N:`` line on the same page.
    """
    raw: list[tuple[int, str, list[list[str]]]] = []  # (page, caption, rows)
    doc = pymupdf.open(pdf_path) if pdf_path is not None else None
    try:
        for page_lines in pages:
            if doc is not None:
                for grid in _find_tables_find_tables(doc[page_lines.page - 1]):
                    raw.append((page_lines.page, "", grid))
            caption = ""
            block: list[list[str]] = []
            for line in page_lines.lines:
                if CAPTION_RE.match(line):
                    caption = clean_caption(line)
                    continue
                row = parse_pipe_row(line)
                if row is not None:
                    block.append(row)
                    continue
                if block:
                    raw.append((page_lines.page, caption, block))
                    caption = ""
                    block = []
            if block:
                raw.append((page_lines.page, caption, block))
    finally:
        if doc is not None:
            doc.close()
    deduped: list[tuple[int, str, list[list[str]]]] = []
    seen: set[str] = set()
    for page, caption, rows in raw:
        key = f"{page}|{json.dumps(rows, sort_keys=True)}"
        if key in seen:
            continue  # finder and pipe fallback read the same table
        seen.add(key)
        deduped.append((page, caption, rows))
    return [
        Table(id=f"t{index}", caption=caption, rows=rows, source="text", page=page)
        for index, (page, caption, rows) in enumerate(deduped, start=1)
    ]


def clean_caption(caption: str) -> str:
    """Strip a leading ``Table N:`` label so captions match across sources."""
    match = CAPTION_PREFIX_RE.match(caption.strip())
    return match.group(1).strip() if match else caption.strip()


def pages_with_tables(pages: list[PageLines], text_tables: list[Table]) -> list[int]:
    """Page numbers worth a vision read: a caption or text table is present."""
    numbered = {table.page or 0 for table in text_tables}
    for page in pages:
        if any(CAPTION_RE.match(line) for line in page.lines):
            numbered.add(page.page)
    return sorted(numbered)


def render_page_png(pdf_path: Path | str, page_number: int, dpi: int = 150) -> bytes:
    """Render one 1-based PDF page to PNG bytes for the vision read."""
    with pymupdf.open(pdf_path) as doc:
        if page_number < 1 or page_number > doc.page_count:
            raise ValueError(f"Page {page_number} out of range (1..{doc.page_count}).")
        pixmap = doc[page_number - 1].get_pixmap(dpi=dpi)
        return pixmap.tobytes("png")


def read_vision_tables(pages_png: list[tuple[int, bytes]], run: RunContext) -> list[VisionTable]:
    """Transcribe tables from page images via the model gateway.

    Args:
        pages_png: ``(page_number, png_bytes)`` pairs.
        run: Per-run context carrying the LLM gateway.

    Raises:
        RuntimeError: If no gateway is attached or the model output is
            not a valid table list.
    """
    gateway = run.llm
    if gateway is None or not hasattr(gateway, "complete"):
        raise RuntimeError("Vision read needs run.llm, but no gateway is attached.")
    vision: list[VisionTable] = []
    for page_number, png in pages_png:
        image_b64 = base64.b64encode(png).decode("ascii")
        result = gateway.complete(  # type: ignore[union-attr]
            task=TABLE_TASK,
            messages=[
                {"role": "system", "content": VISION_SYSTEM},
                {
                    "role": "user",
                    "content": f"Transcribe the tables on page {page_number}. "
                    f"Page image (base64 PNG): {image_b64}",
                },
            ],
            schema=VISION_SCHEMA,
            role="agent",
        )
        vision.extend(_validate_vision_result(result, page_number))
    return vision


def _validate_vision_result(result: Any, page_number: int) -> list[VisionTable]:
    """Validate one ``table_vision`` response. Raises TypeError if invalid."""
    if not isinstance(result, dict) or not isinstance(result.get("tables"), list):
        raise TypeError(f"Vision response for page {page_number} has no 'tables' list.")
    tables = []
    for entry in result["tables"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("rows"), list):
            raise TypeError(f"Vision table on page {page_number} has no 'rows' list.")
        rows = [[str(cell) for cell in row] for row in entry["rows"] if isinstance(row, list)]
        tables.append(
            VisionTable(
                page=page_number, caption=clean_caption(str(entry.get("caption", ""))), rows=rows
            )
        )
    return tables


def pair_and_compare(
    text_tables: list[Table], vision: list[VisionTable]
) -> tuple[list[Table], list[TableMismatch]]:
    """Pair text and vision tables by page and order, then compare cells.

    Vision tables take the paired text table's id so a mismatch points
    at one table; unpaired vision tables get fresh ``tN`` ids. Every
    cell that differs (after stripping) becomes a ``TableMismatch``.
    Row and column indexes are 0-based and include the header row.
    """
    by_page_text: dict[int, list[Table]] = {}
    for table in text_tables:
        by_page_text.setdefault(table.page or 0, []).append(table)
    by_page_vision: dict[int, list[VisionTable]] = {}
    for entry in vision:
        by_page_vision.setdefault(entry.page, []).append(entry)

    used = len(text_tables)
    vision_tables: list[Table] = []
    mismatches: list[TableMismatch] = []
    for page in sorted(set(by_page_text) | set(by_page_vision)):
        texts = by_page_text.get(page, [])
        visions = by_page_vision.get(page, [])
        for index, entry in enumerate(visions):
            if index < len(texts):
                table_id = texts[index].id
                mismatches.extend(compare_cells(table_id, texts[index].rows, entry.rows))
            else:
                used += 1
                table_id = f"t{used}"
            vision_tables.append(
                Table(
                    id=table_id, caption=entry.caption, rows=entry.rows, source="vision", page=page
                )
            )
    return vision_tables, mismatches


def compare_cells(
    table_id: str, text_rows: list[list[str]], vision_rows: list[list[str]]
) -> list[TableMismatch]:
    """List every cell where the two readings differ."""
    mismatches: list[TableMismatch] = []
    for row in range(max(len(text_rows), len(vision_rows))):
        text_row = text_rows[row] if row < len(text_rows) else []
        vision_row = vision_rows[row] if row < len(vision_rows) else []
        for col in range(max(len(text_row), len(vision_row))):
            text_value = text_row[col].strip() if col < len(text_row) else ""
            vision_value = vision_row[col].strip() if col < len(vision_row) else ""
            if text_value != vision_value:
                mismatches.append(
                    TableMismatch(
                        table_id=table_id,
                        row=row,
                        col=col,
                        text_value=text_value,
                        vision_value=vision_value,
                    )
                )
    return mismatches
