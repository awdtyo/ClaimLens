"""Seed demo=true runs from example papers ahead of the full pipeline.

Usage: ``python -m scripts.seed_example_demos [--examples ex1_clean,ex4_untestable]``

Runs the implemented stages (ingest, claims, plan) for real on example
papers and writes the run directories with ``demo=true``. The run state
is honestly marked failed: sandbox and verify are Part 2 stages and
still raise NotImplementedError, so no verdicts are fabricated (hard
rule 6: only the verification stage resolves claims).
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def seed_demo(name: str, runs_root: Path, work_root: Path) -> str:
    """Build one demo run from an example paper. Returns the run id."""
    from claimlens.api import state as state_mod
    from claimlens.ingest import pdf_text, tables
    from claimlens.pipeline import make_run_context, run_stage
    from scripts.evaluate import build_pdf, load_example, write_fake_override

    directory, expected = load_example(name)
    pdf_path = build_pdf(directory, expected)
    doc = pdf_text.extract_pages(pdf_path)
    text_tables = tables.extract_text_tables(doc.pages, pdf_path=pdf_path)
    override = write_fake_override(
        directory, expected, [table.model_dump(mode="json") for table in text_tables]
    )
    os.environ["CLAIMLENS_PROVIDER"] = "fake"
    os.environ["CLAIMLENS_NO_SLEEP"] = "1"
    os.environ["CLAIMLENS_FAKE_RESPONSES"] = str(override)
    os.environ["CLAIMLENS_CACHE_DIR"] = str(work_root / name / "llm_cache")

    run_id = state_mod.new_run_id()
    run_dir = state_mod.run_dir_for(runs_root, run_id)
    run = make_run_context(run_id, runs_root=runs_root)
    # Point the context at the final demo dir (make_run_context created it).
    assert Path(run.run_dir) == run_dir  # type: ignore[arg-type]
    shutil.copyfile(pdf_path, run_dir / state_mod.PAPER_FILENAME)

    state = state_mod.new_state(run_id, filename=f"{name}.pdf", demo=True)
    state["status"] = "running"
    state_mod.write_state(run_dir, state)
    run.emit("run", "started", f"demo run for {name}")
    parsed = run_stage("ingest", run, {"pdf_path": pdf_path})
    state_mod.mark_stage(run_dir, "ingest", "done", started=True, ended=True)
    claims = run_stage("claims", run, {"parsed": parsed})
    state_mod.mark_stage(run_dir, "claims", "done", started=True, ended=True)
    run_stage("plan", run, {"parsed": parsed, "claims": claims})
    state_mod.mark_stage(run_dir, "plan", "done", started=True, ended=True)

    blocked = "blocked: sandbox and verify stages are not implemented yet (Part 2)"
    try:
        run_stage("sandbox", run, {})
    except NotImplementedError as exc:
        blocked = f"blocked: sandbox stage not implemented yet (Part 2): {exc}"
    state_mod.mark_stage(run_dir, "sandbox", "failed", error=blocked, started=True, ended=True)
    run.emit("run", "failed", blocked)
    final = state_mod.read_state(run_dir)
    assert final is not None
    final["status"] = "failed"
    final["error"] = blocked
    state_mod.write_state(run_dir, final)
    return run_id


def main(argv: list[str] | None = None) -> int:
    """Seed demo runs for the given examples."""
    import tempfile

    parser = argparse.ArgumentParser(description="Seed demo runs from example papers.")
    parser.add_argument(
        "--examples", default="ex1_clean,ex4_untestable", help="Comma-separated example names."
    )
    parser.add_argument("--runs-root", default="runs", help="Runs directory.")
    args = parser.parse_args(argv)
    runs_root = REPO_ROOT / args.runs_root
    scratch = tempfile.TemporaryDirectory(prefix="claimlens-demo-")
    work_root = Path(scratch.name)
    for name in [item for item in args.examples.split(",") if item]:
        run_id = seed_demo(name, runs_root, work_root)
        print(f"{name}: {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
