"""Mock pipeline: replay canned fixtures stage by stage.

Enabled with ``CLAIMLENS_MOCK_PIPELINE=1`` so the frontend can be built
before the real stages exist. No stage logic runs here; artifacts are
copied from ``tests/fixtures/mock_*.json`` with short delays and
realistic progress events.

``CLAIMLENS_MOCK_DELAY`` overrides the per-step delay in seconds
(``0`` disables sleeping; used by tests).
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from pathlib import Path
from typing import Any

from claimlens import artifacts
from claimlens.api import state as state_mod
from claimlens.artifacts import STAGE_ORDER
from claimlens.claims.schema import Claim, Evidence, ParsedPaper, Plan, Verdict
from claimlens.config import RunContext

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"

MOCK_FIXTURES: dict[str, str] = {
    "ingest": "mock_parsed.json",
    "claims": "mock_claims.json",
    "plan": "mock_plan.json",
    "sandbox": "mock_evidence.json",
    "verify": "mock_verdicts.json",
}

MOCK_REPORT_FIXTURE = "mock_report.md"

PLACEHOLDER_PDF = b"%PDF-1.4\n%mock placeholder\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"

MOCK_PROGRESS: dict[str, list[str]] = {
    "ingest": [
        "reading PDF text layer",
        "extracting Table 1 from page 2",
        "flagging 1 text/vision table mismatch",
    ],
    "claims": [
        "scanning sections for testable statements",
        "found 4 testable claims",
    ],
    "plan": [
        "matching claims to reproduction steps",
        "logging 3 assumptions",
    ],
    "sandbox": [
        "agent: wrote train_x.py",
        "agent: running docker container (10% subsample)",
        "agent: epoch 10/10 loss 0.31",
        "agent: measured accuracy 91.1%",
        "agent: sensitivity rerun with seed 1 -> 82.4%",
        "agent: sensitivity rerun with noise rate 0.05 -> 84.0%",
    ],
    "verify": [
        "comparing measured vs reported numbers",
        "2 sensitivity reruns attached as assumption effects",
        "4 verdicts: replicated, partially replicated, not replicated, untestable",
    ],
    "report": [
        "writing report.md",
    ],
}


def fixture_path(name: str) -> Path:
    """Fixed fixture location for a mock artifact file name."""
    return FIXTURES_DIR / name


def load_mock_payload(stage: str) -> Any:
    """Load and schema-validate the mock payload for a stage."""
    with fixture_path(MOCK_FIXTURES[stage]).open(encoding="utf-8") as f:
        data = json.load(f)
    if stage == "ingest":
        return ParsedPaper.model_validate(data)
    if stage == "claims":
        return [Claim.model_validate(item) for item in data]
    if stage == "plan":
        return Plan.model_validate(data)
    if stage == "sandbox":
        return [Evidence.model_validate(item) for item in data]
    if stage == "verify":
        return [Verdict.model_validate(item) for item in data]
    raise ValueError(f"No mock fixture for stage {stage!r}.")


def mock_delay() -> float:
    """Per-step delay in seconds; ``CLAIMLENS_MOCK_DELAY`` overrides it."""
    override = os.environ.get("CLAIMLENS_MOCK_DELAY")
    if override is not None:
        return max(0.0, float(override))
    return random.uniform(0.05, 0.25)


def is_cancelled(run_dir: Path | str) -> bool:
    """Check whether a run was cancelled via its state file."""
    current = state_mod.read_state(run_dir)
    return current is not None and current.get("status") == "cancelled"


async def _nap() -> None:
    delay = mock_delay()
    if delay > 0:
        await asyncio.sleep(delay)


async def replay_mock_pipeline(run: RunContext) -> None:
    """Replay mock fixtures stage by stage, emitting realistic events."""
    run_dir = Path(run.run_dir)  # type: ignore[arg-type]
    run.emit("run", "started", "mock pipeline started")
    for stage in STAGE_ORDER:
        if is_cancelled(run_dir):
            return
        state_mod.mark_stage(run_dir, stage, "running", started=True)
        run.emit(stage, "started", f"{stage} started")
        await _nap()
        if stage == "report":
            report_text = fixture_path(MOCK_REPORT_FIXTURE).read_text(encoding="utf-8")
            (run_dir / state_mod.REPORT_FILENAME).write_text(report_text, encoding="utf-8")
            artifacts.save_artifact(run_dir, "report", run_dir / state_mod.REPORT_FILENAME)
        else:
            payload = load_mock_payload(stage)
            artifacts.save_artifact(run_dir, stage, payload)
        for message in MOCK_PROGRESS[stage]:
            if is_cancelled(run_dir):
                return
            run.emit(stage, "progress", message)
            await _nap()
        state_mod.mark_stage(run_dir, stage, "done", ended=True)
        run.emit(stage, "done", f"{stage} done")
    current = state_mod.read_state(run_dir)
    if current is not None and current.get("status") != "cancelled":
        current["status"] = "done"
        state_mod.write_state(run_dir, current)
        run.emit("run", "done", "mock pipeline done")


def write_mock_run(
    run_dir: Path,
    run_id: str,
    filename: str,
    demo: bool = False,
) -> dict[str, Any]:
    """Write a finished mock run synchronously (used for demo seeding)."""
    from claimlens.config import ClaimLensConfig

    run_dir.mkdir(parents=True, exist_ok=True)
    if not (run_dir / state_mod.PAPER_FILENAME).exists():
        (run_dir / state_mod.PAPER_FILENAME).write_bytes(PLACEHOLDER_PDF)
    run = RunContext(
        run_id=run_id,
        run_dir=run_dir,
        config=ClaimLensConfig.from_env(),
        llm=None,
    )
    current_state = state_mod.new_state(run_id, filename, demo=demo)
    current_state["status"] = "running"
    state_mod.write_state(run_dir, current_state)
    run.emit("run", "started", "mock pipeline started")
    for stage in STAGE_ORDER:
        state_mod.mark_stage(run_dir, stage, "running", started=True)
        run.emit(stage, "started", f"{stage} started")
        if stage == "report":
            report_text = fixture_path(MOCK_REPORT_FIXTURE).read_text(encoding="utf-8")
            (run_dir / state_mod.REPORT_FILENAME).write_text(report_text, encoding="utf-8")
            artifacts.save_artifact(run_dir, "report", run_dir / state_mod.REPORT_FILENAME)
        else:
            artifacts.save_artifact(run_dir, stage, load_mock_payload(stage))
        for message in MOCK_PROGRESS[stage]:
            run.emit(stage, "progress", message)
        state_mod.mark_stage(run_dir, stage, "done", ended=True)
        run.emit(stage, "done", f"{stage} done")
    current_state["status"] = "done"
    state_mod.write_state(run_dir, current_state)
    run.emit("run", "done", "mock pipeline done")
    final = state_mod.read_state(run_dir)
    assert final is not None
    return final


def seed_demo_runs(runs_root: Path | str) -> list[str]:
    """Ensure two finished demo runs exist. Returns their run ids."""
    from claimlens.api.state import new_run_id, run_dir_for

    root = Path(runs_root)
    existing = [s for s in state_mod.list_runs(root) if s.get("demo") is True]
    if len(existing) >= 2:
        return [s["run_id"] for s in existing[:2]]
    seeded = [s["run_id"] for s in existing]
    needed = 2 - len(seeded)
    for index in range(needed):
        run_id = new_run_id()
        run_dir = run_dir_for(root, run_id)
        write_mock_run(
            run_dir, run_id, filename=f"demo-paper-{len(seeded) + index + 1}.pdf", demo=True
        )
        seeded.append(run_id)
    return seeded
