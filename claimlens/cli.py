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


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
