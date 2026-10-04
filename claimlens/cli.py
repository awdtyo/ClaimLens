"""CLI for ClaimLens."""

from __future__ import annotations

from pathlib import Path

import typer

from claimlens.artifacts import STAGE_ORDER
from claimlens.config import ClaimLensConfig
from claimlens.pipeline import make_run_context, run_pipeline, run_stage

app = typer.Typer(help="Audit a research paper claim by claim.")


@app.command()
def run(
    pdf: Path = typer.Argument(..., help="Path to the paper PDF."),
    out: Path = typer.Option(Path("runs"), "--out", help="Runs output directory."),
    run_id: str | None = typer.Option(None, "--run-id", help="Run id to use."),
    from_stage: str = typer.Option(
        "ingest", "--from-stage", help=f"Resume from stage: {', '.join(STAGE_ORDER)}."
    ),
) -> None:
    """Run the full audit pipeline on a paper PDF."""
    run_ctx = run_pipeline(pdf_path=pdf, run_id=run_id, runs_root=out, from_stage=from_stage)
    typer.echo(f"run_id={run_ctx.run_id} dir={run_ctx.run_dir}")


@app.command()
def stage(
    name: str = typer.Argument(..., help=f"Stage name: {', '.join(STAGE_ORDER)}."),
    run_id: str = typer.Option(..., "--run-id", help="Existing run id."),
    out: Path = typer.Option(Path("runs"), "--out", help="Runs output directory."),
    pdf: Path | None = typer.Option(None, "--pdf", help="Paper PDF (for ingest)."),
) -> None:
    """Run a single stage, loading prior artifacts from the run directory."""
    if name not in STAGE_ORDER:
        raise typer.BadParameter(f"Unknown stage {name!r}. Choose from {STAGE_ORDER}.")
    config = ClaimLensConfig.from_env()
    run_ctx = make_run_context(run_id, runs_root=out, config=config)
    inputs: dict[str, object] = {}
    if pdf is not None:
        inputs["pdf_path"] = pdf
    result = run_stage(name, run_ctx, inputs=inputs)
    typer.echo(f"stage={name} run_id={run_id} result={type(result).__name__}")


@app.command()
def report(
    run_id: str = typer.Argument(..., help="Run id to render the report for."),
    out: Path = typer.Option(Path("runs"), "--out", help="Runs output directory."),
) -> None:
    """Render the verdict report for a finished run."""
    config = ClaimLensConfig.from_env()
    run_ctx = make_run_context(run_id, runs_root=out, config=config)
    path = run_stage("report", run_ctx)
    typer.echo(str(path))


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind."),
    port: int = typer.Option(8000, "--port", help="Port to bind."),
    prod: bool = typer.Option(
        False, "--prod", help="Production mode: serve web/dist if it exists."
    ),
) -> None:
    """Serve the ClaimLens web API with uvicorn."""
    import os

    import uvicorn

    from claimlens.api.app import create_app

    if prod:
        os.environ["CLAIMLENS_PROD"] = "1"
    uvicorn.run(create_app(), host=host, port=port)


@app.command(name="export-openapi")
def export_openapi(
    out: Path = typer.Option(Path("docs/openapi.json"), "--out", help="Where to write the schema."),
) -> None:
    """Write the API schema to docs/openapi.json for the frontend."""
    import json

    from claimlens.api.app import create_app

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(create_app().openapi(), f, indent=2)
        f.write("\n")
    typer.echo(str(out))


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
