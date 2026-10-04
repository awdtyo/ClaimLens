"""Run API: upload, list, detail, events (SSE), artifacts, cancel."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from claimlens.api import state as state_mod
from claimlens.api.mock import replay_mock_pipeline
from claimlens.api.state import (
    TERMINAL_STATUSES,
    list_runs,
    mark_stage,
    new_run_id,
    new_state,
    read_state,
    run_dir_for,
    write_state,
)
from claimlens.artifacts import STAGE_ORDER
from claimlens.config import ClaimLensConfig
from claimlens.events import read_events, subscribe, unsubscribe

MAX_UPLOAD_BYTES = 30 * 1024 * 1024

router = APIRouter()


class Health(BaseModel):
    """Liveness response."""

    status: str


class ConfigInfo(BaseModel):
    """Public runtime config. Never includes API keys."""

    provider: str
    model_planner: str
    model_agent: str
    model_fast: str


class CreateRunResponse(BaseModel):
    """Ids for a newly accepted run."""

    run_id: str


class StageState(BaseModel):
    """Status and timestamps for one pipeline stage."""

    status: str
    started_at: str | None = None
    ended_at: str | None = None
    error: str | None = None


class RunSummary(BaseModel):
    """One row of the run list."""

    run_id: str
    status: str
    demo: bool = False
    filename: str = ""
    created_at: str = ""
    updated_at: str = ""


class RunDetail(RunSummary):
    """Full run state including per-stage status."""

    error: str | None = None
    stages: dict[str, StageState] = {}


ARTIFACT_FILES: dict[str, tuple[str, str]] = {
    "parsed": (state_mod.ARTIFACT_JSON_FILES["parsed"], "application/json"),
    "claims": (state_mod.ARTIFACT_JSON_FILES["claims"], "application/json"),
    "plan": (state_mod.ARTIFACT_JSON_FILES["plan"], "application/json"),
    "evidence": (state_mod.ARTIFACT_JSON_FILES["evidence"], "application/json"),
    "verdicts": (state_mod.ARTIFACT_JSON_FILES["verdicts"], "application/json"),
    "report": (state_mod.REPORT_FILENAME, "text/markdown"),
    "paper": (state_mod.PAPER_FILENAME, "application/pdf"),
}


def _summarize(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": state["run_id"],
        "status": state["status"],
        "demo": state.get("demo", False),
        "filename": state.get("filename", ""),
        "created_at": state.get("created_at", ""),
        "updated_at": state.get("updated_at", ""),
    }


def _resolve_run_dir(request: Request, run_id: str) -> Path:
    try:
        run_dir = run_dir_for(request.app.state.runs_root, run_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Unknown run.") from None
    if read_state(run_dir) is None:
        raise HTTPException(status_code=404, detail="Unknown run.")
    return run_dir


async def _execute_run(request_state: Any, run_id: str) -> None:
    """Background worker: run the mock or real pipeline for one run."""
    runs_root: Path = request_state.runs_root
    config: ClaimLensConfig = request_state.config
    semaphore: asyncio.Semaphore = request_state.semaphore
    run_dir = run_dir_for(runs_root, run_id)
    async with semaphore:
        current = read_state(run_dir)
        if current is None or current.get("status") == "cancelled":
            return
        current["status"] = "running"
        write_state(run_dir, current)
        try:
            if config.mock_pipeline:
                from claimlens.config import RunContext

                run = RunContext(run_id=run_id, run_dir=run_dir, config=config, llm=None)
                await replay_mock_pipeline(run)
            else:
                await asyncio.to_thread(_run_real_pipeline, run_dir, run_id, runs_root, config)
        except Exception as exc:  # noqa: BLE001 - recorded in state for the UI
            failed = read_state(run_dir) or new_state(run_id, "")
            if failed.get("status") != "cancelled":
                failed["status"] = "failed"
                failed["error"] = str(exc)
                write_state(run_dir, failed)
                for stage in STAGE_ORDER:
                    entry = failed["stages"].get(stage, {})
                    if entry.get("status") not in ("done",):
                        mark_stage(run_dir, stage, "failed", error=str(exc))
                        break
                from claimlens.events import append_event

                append_event(run_dir, run_id, "run", "failed", str(exc))


def _run_real_pipeline(
    run_dir: Path, run_id: str, runs_root: Path, config: ClaimLensConfig
) -> None:
    """Run the real stage pipeline in a worker thread (stub stages)."""
    from claimlens.events import append_event
    from claimlens.pipeline import make_run_context, run_pipeline

    append_event(run_dir, run_id, "run", "started", "pipeline started")
    run = make_run_context(run_id, runs_root=runs_root, config=config)
    run_pipeline(
        pdf_path=run_dir / state_mod.PAPER_FILENAME,
        run_id=run_id,
        runs_root=runs_root,
        config=config,
    )
    _ = run
    append_event(run_dir, run_id, "run", "done", "pipeline done")


def schedule_run(request: Request, run_id: str) -> None:
    """Start the background worker for a run."""
    task = asyncio.create_task(_execute_run(request.app.state, run_id))
    request.app.state.tasks.add(task)
    task.add_done_callback(request.app.state.tasks.discard)


@router.get("/health", response_model=Health)
def get_health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/config", response_model=ConfigInfo)
def get_config(request: Request) -> dict[str, str]:
    """Public config: provider and model names only, never keys."""
    config: ClaimLensConfig = request.app.state.config
    return {
        "provider": config.provider,
        "model_planner": config.model_planner,
        "model_agent": config.model_agent,
        "model_fast": config.model_fast,
    }


@router.post("/runs", response_model=CreateRunResponse, status_code=202)
async def create_run(request: Request, file: UploadFile = File(...)) -> dict[str, str]:
    """Accept a paper PDF and start the pipeline in a background worker."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Upload must be application/pdf.")
    size = 0
    chunks: list[bytes] = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="PDF exceeds 30 MB.")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Upload is not a PDF file.")
    run_id = new_run_id()
    run_dir = run_dir_for(request.app.state.runs_root, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / state_mod.PAPER_FILENAME).write_bytes(data)
    write_state(run_dir, new_state(run_id, filename=file.filename or "paper.pdf"))
    schedule_run(request, run_id)
    return {"run_id": run_id}


@router.get("/runs", response_model=list[RunSummary])
def get_runs(request: Request, demo: bool | None = Query(default=None)) -> list[dict[str, Any]]:
    """List runs, oldest first. ``?demo=true`` shows only demo runs."""
    runs = [_summarize(s) for s in list_runs(request.app.state.runs_root)]
    if demo is None:
        return runs
    return [s for s in runs if s["demo"] is demo]


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(request: Request, run_id: str) -> dict[str, Any]:
    """Run detail with per-stage status, timestamps and errors."""
    run_dir = _resolve_run_dir(request, run_id)
    current = read_state(run_dir)
    assert current is not None
    return {**_summarize(current), "error": current.get("error"), "stages": current["stages"]}


def _sse_line(event: dict[str, Any]) -> str:
    import json as json_mod

    return f"data: {json_mod.dumps(event)}\n\n"


def _is_terminal_run_event(event: dict[str, Any]) -> bool:
    return event.get("stage") == "run" and event.get("status") in ("done", "failed")


@router.get("/runs/{run_id}/events")
async def stream_run_events(request: Request, run_id: str) -> StreamingResponse:
    """SSE stream: replay ``events.jsonl``, then stream live events."""
    run_dir = _resolve_run_dir(request, run_id)

    async def generate():  # type: ignore[no-untyped-def]
        queue = subscribe(run_id)
        try:
            sent = 0
            for event in read_events(run_dir):
                yield _sse_line(event)
                sent += 1
                if _is_terminal_run_event(event):
                    return
            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield _sse_line(event)
                    sent += 1
                    if _is_terminal_run_event(event):
                        return
                except TimeoutError:
                    for event in read_events(run_dir)[sent:]:
                        yield _sse_line(event)
                        sent += 1
                        if _is_terminal_run_event(event):
                            return
                    current = read_state(run_dir)
                    if current is not None and current.get("status") in TERMINAL_STATUSES:
                        remaining = read_events(run_dir)[sent:]
                        for event in remaining:
                            yield _sse_line(event)
                            sent += 1
                        if not remaining or _is_terminal_run_event(read_events(run_dir)[-1]):
                            return
        finally:
            unsubscribe(run_id, queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/runs/{run_id}/{artifact}")
def get_run_artifact(request: Request, run_id: str, artifact: str) -> FileResponse:
    """Fetch one run artifact. Names are whitelisted; paths are fixed."""
    if artifact not in ARTIFACT_FILES:
        raise HTTPException(status_code=404, detail="Unknown artifact.")
    run_dir = _resolve_run_dir(request, run_id)
    filename, media_type = ARTIFACT_FILES[artifact]
    path = run_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not ready.")
    return FileResponse(path, media_type=media_type, filename=filename)


@router.post("/runs/{run_id}/cancel", response_model=RunDetail)
def cancel_run(request: Request, run_id: str) -> dict[str, Any]:
    """Cancel a queued or running run."""
    run_dir = _resolve_run_dir(request, run_id)
    current = read_state(run_dir)
    assert current is not None
    if current.get("status") not in TERMINAL_STATUSES:
        current["status"] = "cancelled"
        write_state(run_dir, current)
        from claimlens.events import append_event

        append_event(run_dir, run_id, "run", "failed", "cancelled by user")
        current = read_state(run_dir)
        assert current is not None
    return {**_summarize(current), "error": current.get("error"), "stages": current["stages"]}
