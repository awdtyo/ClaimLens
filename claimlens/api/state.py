"""Run state helpers. State lives in ``runs/<run_id>/state.json``.

No database is used. ``run_id`` values are uuid hex strings; every
helper validates them before touching the filesystem, and artifact
files are resolved from fixed whitelists, never from user input.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claimlens.artifacts import STAGE_FILES, STAGE_ORDER

RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")

TERMINAL_STATUSES = ("done", "failed", "cancelled")

ARTIFACT_JSON_FILES: dict[str, str] = {
    "parsed": STAGE_FILES["ingest"],
    "claims": STAGE_FILES["claims"],
    "plan": STAGE_FILES["plan"],
    "evidence": STAGE_FILES["sandbox"],
    "verdicts": STAGE_FILES["verify"],
}

REPORT_FILENAME = "report.md"
PAPER_FILENAME = "paper.pdf"


def utcnow() -> str:
    """Current UTC time as an ISO string."""
    return datetime.now(UTC).isoformat()


def new_run_id() -> str:
    """Generate a uuid hex run id."""
    return uuid.uuid4().hex


def is_valid_run_id(run_id: str) -> bool:
    """Check a run id is a uuid hex string before using it as a path."""
    return bool(RUN_ID_RE.fullmatch(run_id))


def resolve_runs_root(explicit: Path | str | None = None) -> Path:
    """Resolve the runs directory from an override, env, or default."""
    if explicit is not None:
        return Path(explicit)
    return Path(os.environ.get("CLAIMLENS_RUNS_ROOT", "runs"))


def run_dir_for(runs_root: Path | str, run_id: str) -> Path:
    """Return the run directory, validating the id and containing the path.

    Raises:
        ValueError: If the id is not a uuid hex string or the resolved
            path escapes the runs root.
    """
    if not is_valid_run_id(run_id):
        raise ValueError(f"Invalid run id: {run_id!r}.")
    root = Path(runs_root).resolve()
    candidate = (root / run_id).resolve()
    if candidate.parent != root:
        raise ValueError(f"Invalid run id: {run_id!r}.")
    return candidate


def fresh_stage_states() -> dict[str, dict[str, Any]]:
    """Initial per-stage states for a new run."""
    return {
        stage: {
            "status": "pending",
            "started_at": None,
            "ended_at": None,
            "error": None,
        }
        for stage in STAGE_ORDER
    }


def new_state(run_id: str, filename: str, demo: bool = False) -> dict[str, Any]:
    """Build the initial state dict for a run."""
    now = utcnow()
    return {
        "run_id": run_id,
        "status": "queued",
        "demo": demo,
        "filename": filename,
        "created_at": now,
        "updated_at": now,
        "error": None,
        "stages": fresh_stage_states(),
    }


def state_path(run_dir: Path | str) -> Path:
    """Fixed state file location inside a run directory."""
    return Path(run_dir) / "state.json"


def read_state(run_dir: Path | str) -> dict[str, Any] | None:
    """Read a run's state, or None if it does not exist."""
    path = state_path(run_dir)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_state(run_dir: Path | str, state: dict[str, Any]) -> None:
    """Write a run's state, bumping ``updated_at``."""
    directory = Path(run_dir)
    directory.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = utcnow()
    with state_path(directory).open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def mark_stage(
    run_dir: Path | str,
    stage: str,
    status: str,
    error: str | None = None,
    started: bool = False,
    ended: bool = False,
) -> dict[str, Any] | None:
    """Update one stage entry in the state file."""
    state = read_state(run_dir)
    if state is None:
        return None
    entry = state["stages"].get(stage, {})
    entry["status"] = status
    if started:
        entry["started_at"] = utcnow()
    if ended:
        entry["ended_at"] = utcnow()
    if error is not None:
        entry["error"] = error
    state["stages"][stage] = entry
    write_state(run_dir, state)
    return state


def list_runs(runs_root: Path | str) -> list[dict[str, Any]]:
    """List all runs that have a state file, oldest first."""
    root = Path(runs_root)
    if not root.exists():
        return []
    runs = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or not is_valid_run_id(child.name):
            continue
        state = read_state(child)
        if state is not None:
            runs.append(state)
    runs.sort(key=lambda s: s.get("created_at", ""))
    return runs
