"""Run event bus.

Stages report progress through ``RunContext.emit``, which appends an
event to ``runs/<run_id>/events.jsonl`` and notifies live SSE
subscribers. This module owns the subscriber registry so that
``claimlens.config`` does not depend on the API layer.
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VALID_STATUSES = ("started", "progress", "done", "failed")

_lock = threading.Lock()
_subscribers: dict[str, list[tuple[Any, asyncio.Queue]]] = {}


def append_event(
    run_dir: Path | str,
    run_id: str,
    stage: str,
    status: str,
    message: str | None = None,
    data: Any = None,
) -> dict[str, Any]:
    """Append an event to ``events.jsonl`` and notify live subscribers.

    Args:
        run_dir: Run directory holding ``events.jsonl``.
        run_id: Run the event belongs to.
        stage: Stage name, ``agent``, or ``run`` for run-level events.
        status: One of ``started``, ``progress``, ``done``, ``failed``.
        message: Short human-readable note.
        data: Optional JSON-serialisable payload.

    Raises:
        ValueError: If ``status`` is not a known event status.
    """
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Unknown event status {status!r}. Choose from {VALID_STATUSES}."
        )
    event: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "stage": stage,
        "status": status,
        "message": message,
        "data": data,
    }
    directory = Path(run_dir)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    with _lock:
        targets = list(_subscribers.get(run_id, ()))
    for loop, queue in targets:
        try:
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(queue.put_nowait, event)
            else:
                queue.put_nowait(event)
        except RuntimeError:
            continue
    return event


def subscribe(run_id: str) -> asyncio.Queue:
    """Register a live subscriber queue for a run."""
    try:
        loop: Any = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    queue: asyncio.Queue = asyncio.Queue()
    with _lock:
        _subscribers.setdefault(run_id, []).append((loop, queue))
    return queue


def unsubscribe(run_id: str, queue: asyncio.Queue) -> None:
    """Remove a previously registered subscriber queue."""
    with _lock:
        remaining = [item for item in _subscribers.get(run_id, []) if item[1] is not queue]
        if remaining:
            _subscribers[run_id] = remaining
        else:
            _subscribers.pop(run_id, None)


def read_events(run_dir: Path | str) -> list[dict[str, Any]]:
    """Read all events recorded for a run so far."""
    path = Path(run_dir) / "events.jsonl"
    if not path.exists():
        return []
    events = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events
