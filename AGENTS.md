# AGENTS.md

Instructions for coding agents working on ClaimLens. Read this at the start of every session.

## What this project is

ClaimLens is a CLI tool that audits a computer science research paper claim by claim. Given a paper PDF, it:

1. Extracts testable claims.
2. Plans a reproduction and logs every assumption it has to make.
3. Runs reduced-scale experiments in a Docker sandbox.
4. Compares measured results to the paper's reported numbers in code.
5. Writes a verdict report per claim.

It is an auditor, not a code generator. The output is a verdict for each claim (replicated, partially replicated, not replicated, untestable) with evidence, not just a repository.

## Hard rules

These apply to every change. If a task seems to require breaking one, stop and ask.

1. **Verification is deterministic code.** The model never decides whether results match. Numbers are extracted, normalized and compared in Python with explicit tolerances. No model call is allowed in `verify/compare.py`.
2. **One model gateway.** All model calls go through `claimlens/llm.py`. No other file imports a model SDK.
3. **Gemma 4 only.** The runtime model is Gemma 4. Do not add other model providers' models as defaults.
4. **No silent assumptions.** Every detail the paper omits that the agent fills in is logged with: the detail, the value chosen, the reason, and a confidence level (low, medium, high).
5. **Scaled runs cannot refute a paper.** If an experiment is scaled down, the strongest negative verdict allowed is "partially replicated" or "untestable at this scale". The report must state what the scaled run does and does not show.
6. **Every claim gets a verdict.** The pipeline is not finished until each extracted claim is resolved, including as "untestable". The coding agent may not mark a claim done; only the verification stage can.
7. **Sandbox only.** Generated experiment code runs inside Docker, never on the host.
8. **Table numbers are cross-checked.** Tables are read from the PDF text layer and from page images, and any mismatch is flagged, not silently resolved.

## Models and configuration

Configured through environment variables, read in `config.py`:

- `CLAIMLENS_PROVIDER`: `gemini`, `openrouter` or `ollama`
- `CLAIMLENS_MODEL_PLANNER`: default `gemma-4-31b-it`
- `CLAIMLENS_MODEL_AGENT`: default `gemma-4-26b-a4b-it`
- `CLAIMLENS_MODEL_FAST`: default a small Gemma 4 (E4B)
- `CLAIMLENS_MAX_CONTEXT`: default 30000 tokens
- `GEMINI_API_KEY` or `OPENROUTER_API_KEY` as needed

Rules for `llm.py`:

- Support system prompts, JSON-schema constrained output and function calling.
- Retry with exponential backoff on 429 and 5xx errors.
- Cache responses on disk keyed by model and messages hash to save free-tier quota.
- Log token counts per call to `runs/<run_id>/llm_log.jsonl`.
- Do not assume a 256K context. Chunk by section when the paper exceeds `CLAIMLENS_MAX_CONTEXT`.

Never commit API keys. Keep them in `.env`, which stays in `.gitignore`.

## Repo layout

```
claimlens/
  cli.py          # claimlens run paper.pdf --out runs/ ; claimlens report <run_id>
  llm.py          # single model gateway
  config.py
  ingest/         # pdf_text.py, tables.py
  claims/         # extract.py, schema.py
  plan/           # gaps.py, spec.py
  sandbox/        # docker_runner.py, agent.py, tools.py
  verify/         # compare.py, sensitivity.py
  report/         # render.py
  tests/
  examples/       # small papers with known expected outcomes
```

Data models live in `claims/schema.py` (pydantic): `Claim`, `Assumption`, `Evidence`, `Verdict`.

## Build order

Work one stage at a time. Run the stage's tests before starting the next.

| Stage | Scope | Done when |
|---|---|---|
| 0 | Scaffold, config, schemas, `llm.py` | LLM smoke test returns valid JSON |
| 1 | PDF ingestion and table extraction with cross-check | Mismatches listed for 3 sample papers |
| 2 | Claim extraction to JSON | Every claim has a real `source_ref` |
| 3 | Gap-aware plan and assumption log | No assumption has an empty reason |
| 4 | Docker sandbox | Hello-world runs; over-time scripts are killed and reported |
| 5 | Agent loop with function calling | One easy paper yields a measured value |
| 6 | Verification and sensitivity reruns | Unit tests cover match, near-match, mismatch, untestable |
| 7 | Report rendering | Report readable without opening other files |
| 8 | Evaluation on 3 to 5 papers | Results saved to `docs/eval.md`, including failures |

## Team workflow and ownership

Four people build ClaimLens in parallel through GitHub forks and PRs.
The scaffolding (schemas, stage contracts, fixtures, CI,
contributor docs) is stable. Stage functions are stubs raising
`NotImplementedError` until each part lands its stage.

Ownership:

- Admin: `claimlens/llm.py`, `claimlens/config.py`, `claimlens/cli.py`,
  `claimlens/pipeline.py`, `claimlens/artifacts.py`,
  `claimlens/claims/schema.py`, `claimlens/plan/`, CI, docs, `AGENTS.md`.
- Part A: `claimlens/ingest/`, `claimlens/claims/extract.py`, tests for these.
- Part B: `claimlens/sandbox/`, tests for these.
- Part C: `claimlens/verify/`, `claimlens/report/`, `examples/`,
  `scripts/`, `docs/eval.md`, tests for these.

Rules:

- Edit only your owned paths. Touching another part's paths needs that
  owner's review.
- Schema or contract changes (anything in `docs/CONTRACTS.md` or
  `claimlens/claims/schema.py`) need an issue approved by the admin
  before implementation.
- Develop against the fixtures in `tests/fixtures/` and the toy paper
  in `docs/toy_paper.md`, using the fake LLM provider
  (`CLAIMLENS_PROVIDER=fake`) so no API key is needed.
- Branch naming: `feat/part-a-...`, `feat/part-b-...`,
  `feat/part-c-...` (admin: `feat/admin-...`). Rebase on
  `upstream/main`, keep PRs small (one stage or fix each).
- See `CONTRIBUTING.md` for the full workflow and
  `docs/CONTRACTS.md` for stage inputs and outputs.

## How to work

- Briefly plan before each stage, then implement, then run its acceptance tests.
- Keep functions small and typed. Add tests for every deterministic component.
- If a dependency or model behavior blocks progress, stop and report what you found and the options. Do not work around it silently.
- Commit after each stage with a clear message.
- Do not rewrite files outside the current stage's scope without saying why.

## Code conventions

- Python 3.11 or newer, type hints on public functions, pydantic for structured data.
- Format with `ruff` and test with `pytest`.
- Keep dependencies lean and CPU-friendly. Prefer ChromaDB, ONNX Runtime and local models over heavy stacks where retrieval is needed.
- Do not use Ultralytics or OpenVINO.
- Deterministic tests must use fixed numbers and no network calls.

## Writing style

Reports, README and docs use plain, factual language. No promotional wording. State limits and failures directly.

## Commands

```
pytest                          # run tests
ruff check . && ruff format .   # lint and format
claimlens run paper.pdf --out runs/
claimlens report <run_id>
```

## Definition of done for any change

- Tests pass.
- No hard rule is broken.
- New assumptions, if any, are logged in the assumption log format.
- Behavior changes are reflected in this file or the README.