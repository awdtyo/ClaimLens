"""Ingest tests: toy PDF parsing, vision cross-check, mismatch injection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claimlens import ingest
from claimlens.claims.schema import ParsedPaper
from claimlens.ingest import pdf_text, tables
from claimlens.pipeline import make_run_context


@pytest.fixture()
def isolated_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run context with isolated LLM cache and fake provider."""
    monkeypatch.setenv("CLAIMLENS_PROVIDER", "fake")
    monkeypatch.setenv("CLAIMLENS_NO_SLEEP", "1")
    monkeypatch.setenv("CLAIMLENS_CACHE_DIR", str(tmp_path / "llm_cache"))
    return make_run_context("ingest-test", runs_root=tmp_path / "runs")


def _override_fake_responses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fixtures_dir: Path, vision_rows: list
) -> None:
    canned = json.loads((fixtures_dir / "fake_llm_responses.json").read_text(encoding="utf-8"))
    canned["table_vision"] = {
        "tables": [{"caption": "Test accuracy on dataset D.", "rows": vision_rows}]
    }
    override = tmp_path / "fake_override.json"
    override.write_text(json.dumps(canned), encoding="utf-8")
    monkeypatch.setenv("CLAIMLENS_FAKE_RESPONSES", str(override))


def test_toy_pdf_matches_sample_parsed(
    isolated_run,
    fixtures_dir: Path,  # type: ignore[no-untyped-def]
) -> None:
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    expected = json.loads((fixtures_dir / "sample_parsed.json").read_text(encoding="utf-8"))
    assert parsed.model_dump(mode="json") == expected


def test_every_section_table_and_claim_has_page(
    isolated_run,
    fixtures_dir: Path,  # type: ignore[no-untyped-def]
) -> None:
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    assert parsed.sections
    for section in parsed.sections:
        assert section.page, f"section {section.id} is missing a page"
    assert parsed.tables
    for table in parsed.tables:
        assert table.page, f"table {table.id} is missing a page"


def test_injected_mismatch_is_reported(
    isolated_run,
    tmp_path: Path,
    fixtures_dir: Path,
    monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
) -> None:
    _override_fake_responses(
        tmp_path,
        monkeypatch,
        fixtures_dir,
        [["Method", "Accuracy (%)"], ["X", "91.3"], ["Y (baseline)", "88.0"]],
    )
    parsed = ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    assert len(parsed.table_mismatches) == 1
    mismatch = parsed.table_mismatches[0]
    assert (mismatch.table_id, mismatch.row, mismatch.col) == ("t1", 1, 1)
    assert mismatch.text_value == "91.2"
    assert mismatch.vision_value == "91.3"
    # Both readings are kept; neither is picked silently.
    sources = {(t.id, t.source) for t in parsed.tables}
    assert ("t1", "text") in sources and ("t1", "vision") in sources


def test_progress_events_emitted(
    isolated_run,
    fixtures_dir: Path,  # type: ignore[no-untyped-def]
) -> None:
    from claimlens.events import read_events

    ingest.parse_paper(fixtures_dir / "toy_paper.pdf", isolated_run)
    messages = [event["message"] or "" for event in read_events(isolated_run.run_dir)]  # type: ignore[arg-type]
    assert any("page parsed: 1" in message for message in messages)
    assert any("section parsed: Introduction" in message for message in messages)
    assert any("table extracted: t1" in message for message in messages)


def test_split_sections_skips_preamble_and_numbers() -> None:
    doc = pdf_text.DocumentText(
        title="Title",
        pages=[
            pdf_text.PageLines(
                page=1, lines=["Title", "Preamble, not a section.", "1. Intro", "Body text."]
            ),
            pdf_text.PageLines(page=2, lines=["2. Method", "More text."]),
        ],
    )
    sections = pdf_text.split_sections(doc)
    assert [(s.id, s.title, s.page) for s in sections] == [
        ("s1", "Intro", 1),
        ("s2", "Method", 2),
    ]
    assert sections[0].text == "Body text."


def test_parse_pipe_row() -> None:
    assert tables.parse_pipe_row("| X | 91.2 |") == ["X", "91.2"]
    assert tables.parse_pipe_row("|---|---|") is None
    assert tables.parse_pipe_row("plain line") is None


def test_clean_caption() -> None:
    assert (
        tables.clean_caption("Table 1: Test accuracy on dataset D.")
        == "Test accuracy on dataset D."
    )
    assert tables.clean_caption("No label") == "No label"


def test_compare_cells_flags_every_difference() -> None:
    mismatches = tables.compare_cells("t1", [["a", "b"]], [["a", "c"], ["d"]])
    assert [(m.row, m.col, m.text_value, m.vision_value) for m in mismatches] == [
        (0, 1, "b", "c"),
        (1, 0, "", "d"),
    ]


def test_pages_with_tables_skips_plain_pages() -> None:
    pages = [
        pdf_text.PageLines(page=1, lines=["Just prose."]),
        pdf_text.PageLines(page=2, lines=["Table 1: Caption."]),
    ]
    assert tables.pages_with_tables(pages, []) == [2]


def test_vision_result_validation_rejects_garbage(isolated_run) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(TypeError):
        tables._validate_vision_result({"nope": []}, page_number=2)
    with pytest.raises(TypeError):
        tables._validate_vision_result({"tables": [{"caption": "x"}]}, page_number=2)


def test_parsed_fixture_validates(fixtures_dir: Path) -> None:
    data = json.loads((fixtures_dir / "sample_parsed.json").read_text(encoding="utf-8"))
    assert ParsedPaper.model_validate(data).title
