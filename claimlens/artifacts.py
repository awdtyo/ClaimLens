"""Artifact save/load helpers.

Each pipeline stage writes its output as JSON to
``runs/<run_id>/NN_<stage>.json``. Helpers accept pydantic models,
lists of models, plain dicts/lists, or Paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

STAGE_ORDER: list[str] = ["ingest", "claims", "plan", "sandbox", "code_audit", "verify", "report"]

STAGE_FILES: dict[str, str] = {
    "ingest": "01_ingest.json",
    "claims": "02_claims.json",
    "plan": "03_plan.json",
    "sandbox": "04_sandbox.json",
    "code_audit": "05_code_audit.json",
    "verify": "06_verify.json",
    "report": "07_report.json",
}


def artifact_path(run_dir: Path, stage: str) -> Path:
    """Return the artifact file path for a stage."""
    if stage not in STAGE_FILES:
        raise ValueError(f"Unknown stage: {stage!r}. Expected one of {STAGE_ORDER}.")
    return Path(run_dir) / STAGE_FILES[stage]


def _to_jsonable(payload: Any) -> Any:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    if isinstance(payload, Path):
        return {"path": str(payload)}
    if isinstance(payload, list):
        return [_to_jsonable(item) for item in payload]
    if isinstance(payload, dict):
        return {key: _to_jsonable(value) for key, value in payload.items()}
    return payload


def save_artifact(run_dir: Path, stage: str, payload: Any) -> Path:
    """Save a stage payload to ``runs/<run_id>/NN_<stage>.json``."""
    path = artifact_path(run_dir, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(_to_jsonable(payload), f, indent=2)
        f.write("\n")
    return path


def load_artifact(run_dir: Path, stage: str) -> Any:
    """Load a stage artifact as plain JSON data."""
    path = artifact_path(run_dir, stage)
    with path.open(encoding="utf-8") as f:
        return json.load(f)
