## What this PR does

<!-- One stage or one fix per PR. Link the issue for contract changes. -->

## Checklist

- [ ] Tests pass (`pytest`; the e2e test may `xfail` until stages land).
- [ ] `ruff check .` and `ruff format --check .` are clean.
- [ ] Only my owned paths changed (see CONTRIBUTING.md ownership).
- [ ] No hard rule broken (see AGENTS.md hard rules).
- [ ] New assumptions, if any, are logged in the assumption log format.
- [ ] Contract or schema change has an issue link with admin approval.
- [ ] Web changes: `npm run lint`, `npm run typecheck`, `npm run test`
  and `npm run build` pass from `web/`.
- [ ] API changes: `docs/openapi.json` is regenerated and
  `web/src/api/types.ts` is in sync (`npm run gen:api`).
- [ ] The frontend displays backend verdicts only; it never computes
  or changes a verdict.
