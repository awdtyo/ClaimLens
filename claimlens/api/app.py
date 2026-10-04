"""FastAPI application factory for ClaimLens."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from claimlens.api.runs import router
from claimlens.api.state import resolve_runs_root
from claimlens.config import ClaimLensConfig

VITE_DEV_ORIGIN = "http://localhost:5173"


def repo_root() -> Path:
    """Repository root (parent of the ``claimlens`` package)."""
    return Path(__file__).resolve().parent.parent.parent


def web_dist_dir() -> Path:
    """Built frontend directory, served in production mode if present."""
    return repo_root() / "web" / "dist"


def is_production() -> bool:
    """Production mode flag for static file serving."""
    return os.environ.get("CLAIMLENS_PROD", "0") == "1"


def create_app(
    runs_root: Path | str | None = None,
    config: ClaimLensConfig | None = None,
) -> FastAPI:
    """Build the ClaimLens FastAPI app.

    Args:
        runs_root: Run storage directory override. Defaults to
            ``CLAIMLENS_RUNS_ROOT`` or ``runs``.
        config: Config override. Defaults to ``ClaimLensConfig.from_env()``.
    """
    cfg = config or ClaimLensConfig.from_env()
    root = resolve_runs_root(runs_root)
    root.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.config = cfg
        app.state.runs_root = root
        app.state.semaphore = asyncio.Semaphore(max(1, cfg.max_concurrent_runs))
        app.state.tasks = set()
        if cfg.mock_pipeline:
            from claimlens.api.mock import seed_demo_runs

            seed_demo_runs(root)
        yield
        for task in list(app.state.tasks):
            task.cancel()

    app = FastAPI(title="ClaimLens API", version="0.1.0", lifespan=lifespan)
    # Tests and export-openapi may use app.state before lifespan runs.
    app.state.config = cfg
    app.state.runs_root = root
    app.state.semaphore = asyncio.Semaphore(max(1, cfg.max_concurrent_runs))
    app.state.tasks = set()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[VITE_DEV_ORIGIN],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    if is_production() and web_dist_dir().is_dir():
        app.mount("/", StaticFiles(directory=web_dist_dir(), html=True), name="static")
    return app
