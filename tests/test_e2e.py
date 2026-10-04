"""End-to-end pipeline test on the toy paper.

Marked xfail until the stage logic lands; the scaffolding step only
provides stubs that raise NotImplementedError.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.xfail(reason="Stage logic not implemented yet (scaffolding stubs).")
def test_pipeline_on_toy_paper(tmp_path: Path) -> None:
    from claimlens.pipeline import run_pipeline

    toy_pdf = tmp_path / "toy_paper.pdf"
    toy_pdf.write_bytes(b"%PDF-1.4 toy fixture")
    run = run_pipeline(pdf_path=toy_pdf, run_id="toy", runs_root=tmp_path / "runs")
    report_file = Path(run.run_dir) / "07_report.json"  # type: ignore[arg-type]
    assert report_file.exists()
