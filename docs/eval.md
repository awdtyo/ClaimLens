# Evaluation

Ran 2026-10-04 with the fake LLM provider. Model outputs are canned per example, so this checks the deterministic layers (ingest, claims, plan).

## ex1_clean — PASS

Clean small paper. All numbers agree between prose and Table 1.

Claims checked: 3, assumptions logged: 2.
- BLOCKED sandbox stage not implemented yet (Part 2); verdict comparison pending.
- Expected verdicts (pending verify stage): c1=partially replicated, c2=partially replicated, c3=untestable at this scale.

## ex2_two_tables — PASS

Two tables. Claims point at t1 and t2 respectively.

Claims checked: 2, assumptions logged: 2.
- BLOCKED sandbox stage not implemented yet (Part 2); verdict comparison pending.
- Expected verdicts (pending verify stage): c1=partially replicated, c2=partially replicated.

## ex3_inconsistent — PASS

Documented replication problem: the prose claims 94.1% but Table 1 reports 93.0 for the same method. The text layer and the vision read agree with each other, so no table mismatch is expected; the conflict is between the prose and the table, which ClaimLens records in the claim text but does not score without the verify stage.

Claims checked: 1, assumptions logged: 2.
- BLOCKED sandbox stage not implemented yet (Part 2); verdict comparison pending.
- Expected verdicts (pending verify stage): c1=not replicated.

## ex4_untestable — PASS

c2 has no measurable number and no available dataset, so it is untestable.

Claims checked: 2, assumptions logged: 2.
- BLOCKED sandbox stage not implemented yet (Part 2); verdict comparison pending.
- Expected verdicts (pending verify stage): c1=partially replicated, c2=untestable.

## Failures

- None at the claims/plan level.
- Verdict agreement for all papers is blocked: sandbox and verify are Part 2 stages and still raise NotImplementedError.
