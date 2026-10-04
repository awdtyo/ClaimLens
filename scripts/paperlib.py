"""Deterministic PDF builder for test and example papers.

Generates simple text-based PDFs from lightweight blocks so tests never
depend on copyrighted PDFs. Output is deterministic: fixed fonts,
fixed metadata dates and no random document IDs beyond what PyMuPDF
requires (tests assert on parsed content, not bytes).

Block types (each block is a ``(kind, payload)`` tuple):

- ``("title", text)``: paper title, first page only.
- ``("heading", text)``: section heading, numbered in the source text.
- ``("para", text)``: paragraph, rewrapped to fit the page.
- ``("caption", text)``: table caption, e.g. ``"Table 1: ..."``.
- ``("table", rows)``: table rows; each row is a list of cell strings,
  written as one ``| a | b |`` line per row so the text-layer parser
  can recover the cells.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pymupdf

PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
MARGIN = 72.0
FONT = "helv"
TITLE_SIZE = 18.0
HEADING_SIZE = 14.0
BODY_SIZE = 11.0
LINE_HEIGHT = 14.0
WRAP_WIDTH = 88

Block = tuple[str, Any]
Page = list[Block]


def _wrap(text: str) -> list[str]:
    return textwrap.wrap(text, width=WRAP_WIDTH) or [""]


def render_pdf(path: Path | str, pages: list[Page], title: str = "") -> Path:
    """Render block pages to a PDF file. Returns the output path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    doc.set_metadata(
        {
            "title": title,
            "creator": "claimlens-test",
            "producer": "claimlens-test",
            "creationDate": "D:20240101000000Z",
            "modDate": "D:20240101000000Z",
        }
    )
    for page_blocks in pages:
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        y = MARGIN
        for kind, payload in page_blocks:
            if kind == "title":
                for line in _wrap(str(payload)):
                    page.insert_text((MARGIN, y), line, fontname=FONT, fontsize=TITLE_SIZE)
                    y += TITLE_SIZE + 4.0
                y += 6.0
            elif kind == "heading":
                y += 4.0
                page.insert_text((MARGIN, y), str(payload), fontname=FONT, fontsize=HEADING_SIZE)
                y += LINE_HEIGHT + 4.0
            elif kind in ("para", "caption"):
                for line in _wrap(str(payload)):
                    page.insert_text((MARGIN, y), line, fontname=FONT, fontsize=BODY_SIZE)
                    y += LINE_HEIGHT
                y += 4.0
            elif kind == "table":
                for row in payload:
                    line = "| " + " | ".join(str(cell) for cell in row) + " |"
                    page.insert_text((MARGIN, y), line, fontname=FONT, fontsize=BODY_SIZE)
                    y += LINE_HEIGHT
                y += 4.0
            else:
                raise ValueError(f"Unknown block kind: {kind!r}.")
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    return out


def markdown_to_pages(text: str, page_break_before: str | None = None) -> tuple[str, list[Page]]:
    """Convert a small markdown paper to a title plus block pages.

    Supported constructs: ``# title``, ``## N. Heading`` section
    headings, paragraphs, ``Table N: caption`` lines and ``|`` pipe
    tables. When ``page_break_before`` is given, a new page starts at
    the heading whose title matches it.
    """
    title = ""
    pages: list[Page] = [[]]
    para_lines: list[str] = []

    def flush_para() -> None:
        if para_lines:
            pages[-1].append(("para", " ".join(para_lines)))
            para_lines.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            pages[-1].append(("title", title))
        elif line.startswith("## "):
            flush_para()
            heading = line[3:].strip()
            if page_break_before and heading == page_break_before and pages[-1]:
                pages.append([])
            pages[-1].append(("heading", heading))
        elif line.startswith("Table ") and "|" not in line:
            flush_para()
            pages[-1].append(("caption", line))
        elif line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells and all(set(cell) <= set("-: ") for cell in cells):
                continue  # markdown separator row, not data
            last = pages[-1][-1] if pages[-1] else None
            if last is not None and last[0] == "table":
                last[1].append(cells)
            else:
                pages[-1].append(("table", [cells]))
        elif line == "":
            flush_para()
        else:
            para_lines.append(line)
    flush_para()
    return title, [page for page in pages if page]
