"""Run ClaimLens over examples/ and record agreement in docs/eval.md.

Usage: ``python -m scripts.evaluate [--examples ex1_clean,ex2_two_tables]``

Each example has ``paper.md`` and ``expected.yaml``. Model behavior is
canned per example (fake provider with a generated override), so this
script checks the deterministic layers: section splitting, table
parsing, claim normalization, gap analysis and plan validation.
Verdict comparison stays blocked until the sandbox and verify stages
(Part 2) land; that is recorded, not hidden.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_example(name: str) -> tuple[Path, dict[str, Any]]:
    """Load an example directory's paper and expectations."""
    directory = REPO_ROOT / "examples" / name
    expected = yaml.safe_load((directory / "expected.yaml").read_text(encoding="utf-8"))
    return directory, expected


def build_pdf(directory: Path, expected: dict[str, Any]) -> Path:
    """Generate the example PDF from paper.md (not committed)."""
    from scripts.paperlib import markdown_to_pages, render_pdf

    md_path = directory / "paper.md"
    out_path = directory / "paper.pdf"
    title, pages = markdown_to_pages(
        md_path.read_text(encoding="utf-8"),
        page_break_before=expected.get("page_break_before"),
    )
    return render_pdf(out_path, pages, title=title)


def write_fake_override(
    directory: Path, expected: dict[str, Any], text_tables: list[dict[str, Any]]
) -> Path:
    """Canned model outputs for one example: vision mirrors text tables."""
    from claimlens.claims.schema import Table

    base = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "fake_llm_responses.json").read_text(encoding="utf-8")
    )
    base["table_vision"] = {
        "tables": [
            {"caption": table["caption"], "rows": table["rows"]}
            for table in text_tables
            if Table.model_validate(table).source == "text"
        ]
    }
    base["extract_claims"] = {"claims": expected["claims_raw"]}
    base["build_plan"] = expected["plan_raw"]
    override = directory / "fake_override.json"
    override.write_text(json.dumps(base), encoding="utf-8")
    return override


def check_equal(label: str, got: Any, want: Any, problems: list[str]) -> None:
    """Record a mismatch problem when normalized JSON differs."""
    if json.loads(json.dumps(got, sort_keys=True)) != json.loads(json.dumps(want, sort_keys=True)):
        problems.append(f"{label}: got {got!r}, want {want!r}")


def evaluate_example(name: str, work_root: Path) -> dict[str, Any]:
    """Run the available stages on one example. Returns a result dict."""
    from claimlens.ingest import pdf_text, tables
    from claimlens.pipeline import make_run_context, run_stage

    directory, expected = load_example(name)
    problems: list[str] = []
    pdf_path = build_pdf(directory, expected)

    # Phase 1: text layer only, to mirror it into the vision override.
    doc = pdf_text.extract_pages(pdf_path)
    text_tables = tables.extract_text_tables(doc.pages, pdf_path=pdf_path)
    override = write_fake_override(
        directory, expected, [table.model_dump(mode="json") for table in text_tables]
    )
    os.environ["CLAIMLENS_PROVIDER"] = "fake"
    os.environ["CLAIMLENS_NO_SLEEP"] = "1"
    os.environ["CLAIMLENS_FAKE_RESPONSES"] = str(override)
    os.environ["CLAIMLENS_CACHE_DIR"] = str(work_root / name / "llm_cache")

    run = make_run_context(f"eval-{name}", runs_root=work_root / name / "runs")
    parsed = run_stage("ingest", run, {"pdf_path": pdf_path})
    claims = run_stage("claims", run, {"parsed": parsed})
    plan = run_stage("plan", run, {"parsed": parsed, "claims": claims})

    check_equal("title", parsed.title, expected["title"], problems)
    check_equal(
        "sections",
        [{"id": s.id, "title": s.title, "page": s.page} for s in parsed.sections],
        expected["sections"],
        problems,
    )
    got_tables = [t for t in parsed.tables if t.source == "text"]
    check_equal(
        "tables",
        [
            {"id": t.id, "source": t.source, "page": t.page, "caption": t.caption, "rows": t.rows}
            for t in got_tables
        ],
        expected["tables"],
        problems,
    )
    check_equal(
        "mismatches",
        [m.model_dump(mode="json") for m in parsed.table_mismatches],
        expected.get("mismatches", []),
        problems,
    )
    check_equal(
        "claims",
        [c.model_dump(mode="json") for c in claims],
        expected["claims_expected"],
        problems,
    )
    plan_raw = expected["plan_raw"]
    check_equal(
        "assumptions",
        [
            {
                "id": a.id,
                "detail": a.detail,
                "value_chosen": a.value_chosen,
                "reason": a.reason,
                "confidence": a.confidence,
            }
            for a in plan.assumptions
        ],
        [
            {"id": f"a{i}", **{k: v for k, v in a.items() if k != "id"}}
            for i, a in enumerate(plan_raw["assumptions"], start=1)
        ],
        problems,
    )
    check_equal(
        "plan items",
        [item.model_dump(mode="json") for item in plan.items],
        [
            {
                "claim_id": item["claim_id"],
                "steps": item["steps"],
                "scale_factor": item["scale_factor"],
                "scale_reason": item["scale_reason"],
                "config": item["config"],
            }
            for item in plan_raw["items"]
        ],
        problems,
    )

    try:
        run_stage("sandbox", run, {"plan": plan})
        sandbox_blocked = ""
    except NotImplementedError:
        sandbox_blocked = "sandbox stage not implemented yet (Part 2)"

    return {
        "name": name,
        "problems": problems,
        "claims": len(claims),
        "assumptions": len(plan.assumptions),
        "sandbox_blocked": sandbox_blocked,
        "expected_verdicts": expected.get("expected_verdicts", []),
        "notes": expected.get("notes", ""),
    }


def render_eval_md(results: list[dict[str, Any]]) -> str:
    """Render docs/eval.md from per-example results."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    lines = [
        "# Evaluation",
        "",
        (
            f"Ran {stamp} with the fake LLM provider. Model outputs are canned per "
            "example, so this checks the deterministic layers (ingest, claims, plan)."
        ),
        "",
    ]
    for result in results:
        status = "PASS" if not result["problems"] else "FAIL"
        lines.append(f"## {result['name']} — {status}")
        lines.append("")
        if result["notes"]:
            lines.append(str(result["notes"]).strip())
            lines.append("")
        lines.append(
            f"Claims checked: {result['claims']}, assumptions logged: {result['assumptions']}."
        )
        for problem in result["problems"]:
            lines.append(f"- MISMATCH {problem}")
        if result["sandbox_blocked"]:
            lines.append(f"- BLOCKED {result['sandbox_blocked']}; verdict comparison pending.")
        else:
            lines.append("- Sandbox ran (unexpected before Part 2 lands).")
        if result["expected_verdicts"]:
            wanted = ", ".join(
                f"{v['claim_id']}={v['status']}" for v in result["expected_verdicts"]
            )
            lines.append(f"- Expected verdicts (pending verify stage): {wanted}.")
        lines.append("")
    lines.append("## Failures")
    lines.append("")
    failures = [r for r in results if r["problems"]]
    if failures:
        for result in failures:
            lines.append(f"- {result['name']}: {len(result['problems'])} mismatch(es).")
    else:
        lines.append("- None at the claims/plan level.")
    lines.append(
        "- Verdict agreement for all papers is blocked: sandbox and verify "
        "are Part 2 stages and still raise NotImplementedError."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run evaluation over examples and write docs/eval.md."""
    parser = argparse.ArgumentParser(description="Evaluate ClaimLens on example papers.")
    parser.add_argument(
        "--examples", default="", help="Comma-separated example names (default: all)."
    )
    parser.add_argument("--out", default="docs/eval.md", help="Output markdown path.")
    parser.add_argument("--work-root", default="", help="Scratch dir for runs (default: temp dir).")
    args = parser.parse_args(argv)
    names = [name for name in args.examples.split(",") if name] or sorted(
        path.name for path in (REPO_ROOT / "examples").iterdir() if path.is_dir()
    )
    scratch = tempfile.TemporaryDirectory(prefix="claimlens-eval-")
    work_root = Path(args.work_root) if args.work_root else Path(scratch.name)
    results = [evaluate_example(name, work_root) for name in names]
    out_path = REPO_ROOT / args.out
    out_path.write_text(render_eval_md(results), encoding="utf-8")
    print(str(out_path))
    failed = [result["name"] for result in results if result["problems"]]
    if failed:
        print(f"FAILED: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"OK: {len(results)} examples, verdict comparison blocked on Part 2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
