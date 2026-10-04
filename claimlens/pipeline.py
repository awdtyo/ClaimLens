"""Pipeline: run stages in order, saving artifacts, with resume support."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claimlens import artifacts
from claimlens.artifacts import STAGE_ORDER
from claimlens.claims.schema import Claim, Evidence, ParsedPaper, Plan, Verdict
from claimlens.config import ClaimLensConfig, RunContext
from claimlens.llm import LLMGateway


def make_run_context(
    run_id: str,
    runs_root: Path | str = "runs",
    config: ClaimLensConfig | None = None,
) -> RunContext:
    """Create the run directory and gateway for a run id."""
    cfg = config or ClaimLensConfig.from_env()
    run_dir = Path(runs_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    gateway = LLMGateway(config=cfg, run_dir=run_dir)
    return RunContext(run_id=run_id, run_dir=run_dir, config=cfg, llm=gateway)


def _parse_ingest(data: Any) -> ParsedPaper:
    return ParsedPaper.model_validate(data)


def _parse_claims(data: Any) -> list[Claim]:
    return [Claim.model_validate(item) for item in data]


def _parse_plan(data: Any) -> Plan:
    return Plan.model_validate(data)


def _parse_evidence(data: Any) -> list[Evidence]:
    return [Evidence.model_validate(item) for item in data]


def _parse_verdicts(data: Any) -> list[Verdict]:
    return [Verdict.model_validate(item) for item in data]


def run_stage(
    stage: str,
    run: RunContext,
    inputs: dict[str, Any] | None = None,
) -> Any:
    """Run a single stage, loading missing inputs from saved artifacts.

    Args:
        stage: One of ingest, claims, plan, sandbox, verify, report.
        run: Per-run context.
        inputs: Explicit inputs keyed by artifact name
            (pdf_path, parsed, claims, plan, evidence, verdicts).
            Anything missing is loaded from the run directory.

    Raises:
        FileNotFoundError: If a required prior artifact is missing.
        NotImplementedError: Until the stage logic lands.
    """
    from claimlens import ingest as ingest_mod
    from claimlens import sandbox as sandbox_mod
    from claimlens import verify as verify_mod
    from claimlens.claims import extract as extract_mod
    from claimlens.plan import build as build_mod
    from claimlens.report import render as render_mod

    inputs = dict(inputs or {})
    run_dir = Path(run.run_dir)  # type: ignore[arg-type]

    if stage == "ingest":
        if "pdf_path" not in inputs:
            raise ValueError("ingest stage needs inputs['pdf_path'].")
        parsed = ingest_mod.parse_paper(Path(inputs["pdf_path"]), run)
        artifacts.save_artifact(run_dir, "ingest", parsed)
        return parsed

    if stage == "claims":
        parsed = inputs.get("parsed")
        if parsed is None:
            parsed = _parse_ingest(artifacts.load_artifact(run_dir, "ingest"))
        claims = extract_mod.extract_claims(parsed, run)
        artifacts.save_artifact(run_dir, "claims", claims)
        return claims

    if stage == "plan":
        parsed = inputs.get("parsed")
        if parsed is None:
            parsed = _parse_ingest(artifacts.load_artifact(run_dir, "ingest"))
        claims = inputs.get("claims")
        if claims is None:
            claims = _parse_claims(artifacts.load_artifact(run_dir, "claims"))
        plan = build_mod.build_plan(parsed, claims, run)
        artifacts.save_artifact(run_dir, "plan", plan)
        return plan

    if stage == "sandbox":
        plan = inputs.get("plan")
        if plan is None:
            plan = _parse_plan(artifacts.load_artifact(run_dir, "plan"))
        evidence = sandbox_mod.run_experiments(plan, run)
        artifacts.save_artifact(run_dir, "sandbox", evidence)
        return evidence

    if stage == "verify":
        claims = inputs.get("claims")
        if claims is None:
            claims = _parse_claims(artifacts.load_artifact(run_dir, "claims"))
        plan = inputs.get("plan")
        if plan is None:
            plan = _parse_plan(artifacts.load_artifact(run_dir, "plan"))
        evidence = inputs.get("evidence")
        if evidence is None:
            evidence = _parse_evidence(artifacts.load_artifact(run_dir, "sandbox"))
        verdicts = verify_mod.verify_claims(claims, plan, evidence, run)
        artifacts.save_artifact(run_dir, "verify", verdicts)
        return verdicts

    if stage == "report":
        claims = inputs.get("claims")
        if claims is None:
            claims = _parse_claims(artifacts.load_artifact(run_dir, "claims"))
        plan = inputs.get("plan")
        if plan is None:
            plan = _parse_plan(artifacts.load_artifact(run_dir, "plan"))
        evidence = inputs.get("evidence")
        if evidence is None:
            evidence = _parse_evidence(artifacts.load_artifact(run_dir, "sandbox"))
        verdicts = inputs.get("verdicts")
        if verdicts is None:
            verdicts = _parse_verdicts(artifacts.load_artifact(run_dir, "verify"))
        report_path = render_mod.render_report(claims, plan, evidence, verdicts, run)
        artifacts.save_artifact(run_dir, "report", report_path)
        return report_path

    raise ValueError(f"Unknown stage: {stage!r}. Expected one of {STAGE_ORDER}.")


def run_pipeline(
    pdf_path: Path | str,
    run_id: str | None = None,
    runs_root: Path | str = "runs",
    from_stage: str = "ingest",
    config: ClaimLensConfig | None = None,
) -> RunContext:
    """Run the full pipeline (or resume from a stage).

    Args:
        pdf_path: Path to the paper PDF.
        run_id: Run id; generated from the PDF name and timestamp if omitted.
        runs_root: Parent directory for run output.
        from_stage: Stage to resume from; prior artifacts are loaded.
        config: Optional config override.

    Raises:
        NotImplementedError: Until the stage logic lands.
    """
    if from_stage not in STAGE_ORDER:
        raise ValueError(f"Unknown --from-stage: {from_stage!r}. Expected one of {STAGE_ORDER}.")
    if run_id is None:
        stem = Path(pdf_path).stem
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{stem}-{stamp}"
    run = make_run_context(run_id, runs_root=runs_root, config=config)
    start = STAGE_ORDER.index(from_stage)
    inputs: dict[str, Any] = {"pdf_path": Path(pdf_path)}
    for stage in STAGE_ORDER[start:]:
        result = run_stage(stage, run, inputs=inputs)
        if stage == "ingest":
            inputs["parsed"] = result
        elif stage == "claims":
            inputs["claims"] = result
        elif stage == "plan":
            inputs["plan"] = result
        elif stage == "sandbox":
            inputs["evidence"] = result
        elif stage == "verify":
            inputs["verdicts"] = result
    return run
