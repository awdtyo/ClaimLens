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

- `Claim`: `id`, `text`, `source_ref` (a section or table id from the
  parsed paper, e.g. `t1`; anything else is rejected), `metric`,
  `dataset`, `baseline`, `reported_value` (normalized: percentages and
  percentage points become fractions, so 91.2% is stored as 0.912),
  `tolerance` (same units, default 0.01), `testable` (default true) and
  `page` (PDF page for UI navigation).
- `Assumption`: `id`, `detail`, `value_chosen`, `reason` (never empty),
  `confidence` (`low` | `medium` | `high`).
- `AssumptionEffect`: `assumption_id`, `claim_id`, `alt_value`,
  `measured_value`, `delta`. Records one sensitivity rerun where a
  single assumption was varied.
- `Evidence`: `id`, `claim_id`, `method`, `measured_value`, `config`,
  `logs_ref`, `scale_factor`.
- `Verdict`: `claim_id`, `status` (`replicated` | `partially replicated` |
  `not replicated` | `untestable` | `untestable at this scale`),
  `rationale`, `evidence_ids`, `scaled`, `assumption_effects`
  (list of `AssumptionEffect`, empty when there were no reruns).
- `ParsedPaper`: `title`, `sections` (`Section`: `id`, `title`, `text`,
  `page`), `tables` (`Table`: `id`, `caption`, `rows`, `source`, `page`),
  `table_mismatches` (`TableMismatch`: `table_id`, `row`, `col`,
  `text_value`, `vision_value`).
- `Plan`: `items` (`PlanItem`: `claim_id`, `steps`, `scale_factor`,
  `scale_reason` (why this scale; never empty), `config`), `assumptions`.
- `RunContext.emit(stage, status, message=None, data=None)` appends
  `{"ts", "run_id", "stage", "status", "message", "data"}` to
  `runs/<run_id>/events.jsonl` and notifies live SSE subscribers.
  `status` is one of `started` | `progress` | `done` | `failed`.

## Value normalization

`Claim.reported_value` is stored unit-free: percentages and percentage
points are divided by 100 (91.2% -> 0.912); ratios and counts pass
through. `tolerance` uses the same units. The verify stage must
normalize measured values the same way before comparing.

## Source references

`Claim.source_ref` is always a section or table id (`s1`, `t1`); the
page shown in the UI comes from that section or table. Claims pointing
elsewhere are rejected at extraction.

## Report outputs

`render_report` writes `report.md` (summary table plus per-claim
verdict, numbers, key assumptions, scale limits and log links) and
`report.json` (the verdict list unchanged, each entry validating as a
`Verdict`). The pipeline records the Markdown path in `06_report.json`.

## Examples and evaluation

`examples/<name>/` holds `paper.md` plus `expected.yaml` (expected
sections, tables, normalized claims, plan content and predicted
verdicts). `python -m scripts.evaluate` builds each PDF, runs the
ingest/claims/plan stages with per-example canned model outputs, and
writes agreement results to `docs/eval.md`. Verdict comparison stays
blocked until the sandbox and verify stages land. `python -m
scripts.seed_example_demos` materializes `demo=true` runs from the
examples with the stages implemented so far.

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

## Mock pipeline

With `CLAIMLENS_MOCK_PIPELINE=1`, `claimlens.api.mock` replays
`tests/fixtures/mock_*.json` stage by stage with short random delays
(`CLAIMLENS_MOCK_DELAY` overrides the per-step delay in seconds) and
realistic progress events including agent log lines. The mock run
covers every UI state: one table mismatch, one `replicated` claim, one
`partially replicated` claim, one `not replicated` claim with two
`assumption_effects`, and one `untestable` claim. Two finished runs
with `demo=true` are seeded at server startup.

## Web API

State lives in `runs/<run_id>/state.json`; there is no database.
`run_id` is a uuid hex string. Artifact names are whitelisted
(`parsed`, `claims`, `plan`, `evidence`, `verdicts`, `report`, `paper`);
file paths are never built from user input. CORS allows only the Vite
dev origin. `CLAIMLENS_MAX_CONCURRENT_RUNS` (default 1) bounds parallel
runs; extra runs stay `queued`. The schema is generated with
`claimlens export-openapi` into `docs/openapi.json`; the frontend
regenerates `web/src/api/types.ts` from it with `npm run gen:api`.
