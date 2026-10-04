# ClaimLens verdict report (mock)

Mock reproduction of "Method X Improves Classification Accuracy on
Dataset D". Numbers below are canned fixtures for frontend development,
not real measurements.

## Verdicts

| Claim | Reported | Measured | Verdict |
|-------|----------|----------|---------|
| c1: Method X reaches 91.2% accuracy on dataset D. | 91.2 | 91.1 | replicated |
| c2: Method X trains 2x faster than baseline Y. | 2.0 | 1.7 (scaled 10%) | partially replicated |
| c3: Method X keeps 89.5% accuracy under 10% label noise. | 89.5 | 82.1 | not replicated |
| c4: Method X generalizes to dataset E. | n/a | n/a | untestable |

## Notes

- Table t1 differs between the text layer (91.2) and the vision read
  (91.3). The mismatch is flagged, not resolved.
- c2 ran at 10% scale: a scaled run cannot fully confirm or refute the
  paper.
- c3 sensitivity: seed 1 measures 82.4 (delta +0.3); noise rate 0.05
  measures 84.0 (delta +1.9). The gap persists.
- c4 is untestable: dataset E is not available.
