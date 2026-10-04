# Contributing to ClaimLens

Four people build ClaimLens in parallel through GitHub forks and PRs.
This file defines the workflow. The rule is simple: edit only your
owned paths, and change contracts only through an approved issue.

## Setup

```bash
git clone <your-fork-url> claimlens
cd claimlens
pip install -e ".[dev]"
cp .env.example .env   # fill in keys; .env is never committed
```

No API key is needed for tests. Tests use `CLAIMLENS_PROVIDER=fake`,
which serves canned responses from
`tests/fixtures/fake_llm_responses.json`.

## Fork and branch workflow

1. Fork the repo on GitHub, then clone your fork.
2. Add the team repo as upstream:
   ```bash
   git remote add upstream <team-repo-url>
   ```
3. Before starting work, sync and rebase:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
4. Create a branch per change with the part prefix:
   - `feat/part-a-<stage>-<short-name>` (ingest, claim extraction)
   - `feat/part-b-<stage>-<short-name>` (sandbox)
   - `feat/part-c-<stage>-<short-name>` (verify, report, examples)
   - Admin uses `feat/admin-<short-name>` or `fix/admin-<short-name>`.
5. Keep PRs small: one stage or one fix per PR.
6. Rebase on `upstream/main` before requesting review. Resolve
   conflicts in your own branch.

## Ownership

- Admin: `claimlens/llm.py`, `claimlens/config.py`, `claimlens/cli.py`,
  `claimlens/pipeline.py`, `claimlens/artifacts.py`,
  `claimlens/claims/schema.py`, `claimlens/plan/`, CI, docs, `AGENTS.md`.
- Part A: `claimlens/ingest/`, `claimlens/claims/extract.py`, tests for these.
- Part B: `claimlens/sandbox/`, tests for these.
- Part C: `claimlens/verify/`, `claimlens/report/`, `claimlens/examples/`,
  `scripts/`, `docs/eval.md`, tests for these.

Rule: edit only your owned paths. Touching another part's paths needs
that owner's review.

## Contract changes

Stage signatures in `docs/CONTRACTS.md` and models in
`claimlens/claims/schema.py` are stable interfaces. To change them:

1. Open an issue describing the change and why it is needed.
2. Wait for admin approval on the issue.
3. Reference the issue in the PR.

Unapproved contract changes will not be merged.

## Commit style

- Imperative, short subject line (under 72 chars):
  `Add table cross-check stub for ingest`.
- One logical change per commit.
- Commit after each stage with a clear message.

## Checks before pushing

```bash
ruff check .
ruff format --check .
pytest
```

All three must pass. The end-to-end test is expected to `xfail` until
the stage logic lands. Tests marked `docker` are skipped in CI.
