# ClaimLens

ClaimLens audits a computer science research paper claim by claim.

Given a paper PDF it extracts testable claims, plans a reproduction,
runs reduced-scale experiments in a Docker sandbox, compares measured
results to reported numbers in code, and writes a verdict report per
claim.

## Status

ClaimLens is a web app: a FastAPI backend wrapping the pipeline and a
React frontend. Real stage logic is not implemented yet; stage
functions raise `NotImplementedError`. See `docs/CONTRACTS.md` and
`CONTRIBUTING.md` for the team workflow.

## Backend setup

```bash
pip install -e ".[dev]"
cp .env.example .env   # fill in keys; .env is never committed
claimlens serve        # API on http://localhost:8000
```

## Frontend setup

```bash
cd web
npm ci
npm run dev            # Vite on http://localhost:5173, /api proxied to :8000
```

The start page calls `/api/health` through the Vite proxy to prove the
connection. After changing the API, regenerate the schema and types:

```bash
claimlens export-openapi   # writes docs/openapi.json
cd web && npm run gen:api  # writes web/src/api/types.ts
```

Frontend checks: `npm run lint`, `npm run typecheck`, `npm run test`,
`npm run build`.

## Mock mode

No API key or Docker needed. The mock pipeline replays canned fixtures
stage by stage so the frontend can be built first:

```bash
CLAIMLENS_MOCK_PIPELINE=1 claimlens serve
```

This seeds two finished demo runs and streams realistic events
(including agent log lines) for every new upload. In production mode,
the backend serves the built frontend:

```bash
cd web && npm run build
CLAIMLENS_PROD=1 claimlens serve --prod
```

## Usage

```bash
claimlens run paper.pdf --out runs/
claimlens stage ingest --run-id <id>
claimlens report <run_id>
claimlens --help
```

No API key is needed for tests: set `CLAIMLENS_PROVIDER=fake`.

## Configuration

See `.env.example`. Variables are read in `claimlens/config.py`:

- `CLAIMLENS_PROVIDER`: `gemini`, `openrouter`, `ollama`, or `fake`
- `CLAIMLENS_MODEL_PLANNER` (default `gemma-4-31b-it`)
- `CLAIMLENS_MODEL_AGENT` (default `gemma-4-26b-a4b-it`)
- `CLAIMLENS_MODEL_FAST` (default `gemma-4-e4b-it`)
- `CLAIMLENS_MAX_CONTEXT` (default `30000`)
- `GEMINI_API_KEY` / `OPENROUTER_API_KEY` as needed
- `CLAIMLENS_MOCK_PIPELINE` (`1` replays fixtures instead of real stages)
- `CLAIMLENS_MAX_CONCURRENT_RUNS` (default `1`; extra runs queue)
- `CLAIMLENS_RUNS_ROOT` (default `runs`)

## Limits

Scaled-down runs cannot refute a paper. Verdicts and reports state
what scaled runs do and do not show.
