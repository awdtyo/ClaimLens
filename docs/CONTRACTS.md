# Stage contracts

Stable interfaces between team parts. Changes need an issue and admin
approval. All stages receive a `RunContext` (`run_id`, `run_dir`,
`config`, `llm`) by injection. Artifacts are saved to
`runs/<run_id>/NN_<stage>.json` after each stage.

The toy paper (`docs/toy_paper.md`) is the running example: method X
reaches 91.2% accuracy on dataset D versus 88.0% for baseline Y.

| Stage | Function | Inputs | Outputs | Artifact |
|---|---|---|---|---|
| ingest | `claimlens.ingest.parse_paper(pdf_path: Path, run: RunContext) -> ParsedPaper` | PDF path, `RunContext` | `ParsedPaper`: title, 4 sections (`s1`–`s4`), table `t1` (text source), `table_mismatches` | `01_ingest.json` |
| claims | `claimlens.claims.extract.extract_claims(parsed: ParsedPaper, run: RunContext) -> list[Claim]` | `ParsedPaper`, `RunContext` | `Claim` list: `c1` main claim (91.2 vs 88.0, `source_ref` "Section 4, Table 1"), `c2` baseline (88.0), `c3` gap (+3.2pp) | `02_claims.json` |
| plan | `claimlens.plan.build.build_plan(parsed: ParsedPaper, claims: list[Claim], run: RunContext) -> Plan` | `ParsedPaper`, claims, `RunContext` | `Plan`: one `PlanItem` per claim (`scale_factor` 0.1 for the toy paper), `assumptions` with non-empty reasons | `03_plan.json` |
| sandbox | `claimlens.sandbox.run_experiments(plan: Plan, run: RunContext) -> list[Evidence]` | `Plan`, `RunContext` | `Evidence` list: `e1` (claim `c1`, measured 90.8), `e2` (claim `c2`, measured 87.9) | `04_sandbox.json` |
| verify | `claimlens.verify.verify_claims(claims, plan, evidence, run, runner=None) -> list[Verdict]` | claims, plan, evidence, `RunContext`, optional `runner: (Plan, RunContext) -> list[Evidence]` for Docker-free sensitivity reruns | `Verdict` list, one per claim: `c1`/`c2` partially replicated (scaled), `c3` untestable at this scale. Deterministic code only; no model calls | `05_verify.json` |
| report | `claimlens.report.render.render_report(claims, plan, evidence, verdicts, run) -> Path` | claims, plan, evidence, verdicts, `RunContext` | Path to the rendered report; readable without opening other files | `06_report.json` (report path) |

## Schema notes

- `Claim`: `id`, `text`, `source_ref` (required, real reference), optional
  `metric` and `reported_value`.
- `Assumption`: `detail`, `value_chosen`, `reason` (never empty),
  `confidence` (`low` | `medium` | `high`).
- `Evidence`: `id`, `claim_id`, `method`, `measured_value`, `config`,
  `logs_ref`, `scale_factor`.
- `Verdict`: `claim_id`, `status` (`replicated` | `partially replicated` |
  `not replicated` | `untestable` | `untestable at this scale`),
  `rationale`, `evidence_ids`, `scaled`.
- `ParsedPaper`: `title`, `sections` (`Section`: `id`, `title`, `text`),
  `tables` (`Table`: `id`, `caption`, `rows`, `source`),
  `table_mismatches` (`TableMismatch`: `table_id`, `row`, `col`,
  `text_value`, `vision_value`).
- `Plan`: `items` (`PlanItem`: `claim_id`, `steps`, `scale_factor`,
  `config`), `assumptions`.

## Pipeline and CLI

- `claimlens.pipeline.run_pipeline(pdf_path, run_id?, runs_root?, from_stage?)`
  runs stages in order and supports resuming with `--from-stage`.
- `claimlens run <pdf> --out runs/` runs the full pipeline.
- `claimlens stage <name> --run-id <id>` runs one stage, loading prior
  artifacts.
- `claimlens report <run_id>` renders the report from saved artifacts.

## Model gateway

`claimlens.llm.LLMGateway.complete(task, messages, schema=None,
tools=None, role="agent")` with roles `planner`, `agent`, `fast`.
Providers `gemini`, `openrouter`, `ollama`, `fake`. The `fake` provider
serves `tests/fixtures/fake_llm_responses.json` keyed by `task`.
