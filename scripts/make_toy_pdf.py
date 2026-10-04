"""Generate tests/fixtures/toy_paper.pdf from docs/toy_paper.md.

Run: ``python -m scripts.make_toy_pdf`` or ``python scripts/make_toy_pdf.py``.
The output PDF is committed so tests do not depend on copyrighted PDFs.
"""

from __future__ import annotations

from pathlib import Path

from scripts.paperlib import markdown_to_pages, render_pdf

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> Path:
    """Build the toy paper PDF. Returns the output path."""
    md_path = REPO_ROOT / "docs" / "toy_paper.md"
    out_path = REPO_ROOT / "tests" / "fixtures" / "toy_paper.pdf"
    title, pages = markdown_to_pages(
        md_path.read_text(encoding="utf-8"), page_break_before="3. Experiments"
    )
    return render_pdf(out_path, pages, title=title)


if __name__ == "__main__":
    print(main())
