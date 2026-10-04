"""PDF text-layer extraction: page lines and section splitting."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from claimlens.claims.schema import Section

HEADING_RE = re.compile(r"^(\d+)\.\s+(.+?)\s*$")
CAPTION_RE = re.compile(r"^Table\s+\d+\s*:.*$")


@dataclass(frozen=True)
class PageLines:
    """Raw text lines of one PDF page (1-based page number)."""

    page: int
    lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentText:
    """Title plus per-page text lines of a paper PDF."""

    title: str
    pages: list[PageLines] = field(default_factory=list)


def extract_pages(pdf_path: Path | str) -> DocumentText:
    """Extract the title and per-page text lines from a PDF.

    The title is the first non-empty line of the first page. Lines keep
    PDF reading order; blank lines are dropped.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}.")
    pages: list[PageLines] = []
    title = ""
    with pymupdf.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            lines = [line.strip() for line in page.get_text().splitlines()]
            lines = [line for line in lines if line]
            if number == 1 and lines:
                title = lines[0]
            pages.append(PageLines(page=number, lines=lines))
    if not title and pages and pages[0].lines:
        title = pages[0].lines[0]
    return DocumentText(title=title, pages=pages)


def is_table_line(line: str) -> bool:
    """Check whether a line belongs to a pipe-delimited table block."""
    return line.startswith("|")


def split_sections(doc: DocumentText) -> list[Section]:
    """Split document lines into numbered sections.

    A section starts at a ``N. Title`` heading line. The title line of
    the paper, table captions and pipe-delimited table lines are not
    section text. Text before the first heading is skipped. Each
    section records the 1-based PDF page its heading appears on.
    """
    sections: list[Section] = []
    current_id = 0
    current_title = ""
    current_page = 0
    current_lines: list[str] = []

    def flush() -> None:
        if current_id:
            sections.append(
                Section(
                    id=f"s{current_id}",
                    title=current_title,
                    text=" ".join(current_lines).strip(),
                    page=current_page,
                )
            )

    for page in doc.pages:
        for line in page.lines:
            if page.page == 1 and line == doc.title:
                continue
            match = HEADING_RE.match(line)
            if match and not is_table_line(line):
                flush()
                current_id += 1
                current_title = match.group(2)
                current_page = page.page
                current_lines = []
            elif CAPTION_RE.match(line) or is_table_line(line):
                continue
            elif current_id:
                current_lines.append(line)
    flush()
    return sections
