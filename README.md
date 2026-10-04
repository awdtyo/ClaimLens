# ClaimLens

ClaimLens audits a computer science research paper claim by claim.

Given a paper PDF it extracts testable claims, plans a reproduction,
runs reduced-scale experiments in a Docker sandbox, compares measured
results to reported numbers in code, and writes a verdict report per
claim.

## Status

Team scaffolding skeleton. Stage logic is not implemented yet; stage
functions raise `NotImplementedError`. See `docs/CONTRACTS.md` and
`CONTRIBUTING.md` for the team workflow.

## Install

```bash
pip install -e ".[dev]"
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

## Limits

Scaled-down runs cannot refute a paper. Verdicts and reports state
what scaled runs do and do not show.
