import { describe, expect, it } from "vitest";
import type { Claim, Evidence, Verdict } from "../api/models";
import {
  countVerdicts,
  filterClaimRows,
  joinClaimRows,
  sortClaimRows,
} from "./claims";

const claims: Claim[] = [
  { id: "c1", text: "X reaches 91.2%", source_ref: "Table 1", reported_value: 91.2, page: 2 },
  { id: "c2", text: "2x faster", source_ref: "Section 4", reported_value: 2.0, page: 2 },
  { id: "c3", text: "robust", source_ref: "Section 4", reported_value: 89.5, page: 2 },
  { id: "c4", text: "generalizes", source_ref: "Section 3", reported_value: null, page: 2 },
];

const verdicts: Verdict[] = [
  { claim_id: "c1", status: "replicated", rationale: "ok", evidence_ids: ["e1"], scaled: false, assumption_effects: [] },
  { claim_id: "c2", status: "partially replicated", rationale: "scaled", evidence_ids: ["e2"], scaled: true, assumption_effects: [] },
  { claim_id: "c3", status: "not replicated", rationale: "gap", evidence_ids: ["e3", "e4"], scaled: false, assumption_effects: [] },
  { claim_id: "c4", status: "untestable", rationale: "no data", evidence_ids: [], scaled: false, assumption_effects: [] },
];

const evidence: Evidence[] = [
  { id: "e1", claim_id: "c1", method: "m", measured_value: 91.1, scale_factor: 1.0 },
  { id: "e2", claim_id: "c2", method: "m", measured_value: 1.7, scale_factor: 0.1 },
  { id: "e3", claim_id: "c3", method: "m", measured_value: 82.1, scale_factor: 1.0 },
  { id: "e4", claim_id: "c3", method: "sensitivity", measured_value: 82.4, scale_factor: 1.0 },
];

describe("joinClaimRows", () => {
  it("uses the first backend-listed evidence as the primary measurement", () => {
    const rows = joinClaimRows(claims, verdicts, evidence);
    expect(rows).toHaveLength(4);
    expect(rows.find((r) => r.claim.id === "c3")?.measured).toBe(82.1);
    expect(rows.find((r) => r.claim.id === "c4")?.measured).toBeNull();
    expect(rows.find((r) => r.claim.id === "c2")?.scaleFactor).toBe(0.1);
  });

  it("counts one claim per verdict bucket", () => {
    expect(countVerdicts(joinClaimRows(claims, verdicts, evidence))).toEqual({
      replicated: 1,
      "partially replicated": 1,
      "not replicated": 1,
      untestable: 1,
    });
  });
});

describe("filterClaimRows", () => {
  const rows = joinClaimRows(claims, verdicts, evidence);

  it("filters by verdict bucket and text query", () => {
    expect(
      filterClaimRows(rows, { bucket: "replicated", query: "", scaledOnly: false }),
    ).toHaveLength(1);
    expect(
      filterClaimRows(rows, { bucket: "all", query: "faster", scaledOnly: false })[0].claim.id,
    ).toBe("c2");
  });

  it("filters to scaled runs", () => {
    const scaled = filterClaimRows(rows, { bucket: "all", query: "", scaledOnly: true });
    expect(scaled.map((r) => r.claim.id)).toEqual(["c2"]);
  });
});

describe("sortClaimRows", () => {
  const rows = joinClaimRows(claims, verdicts, evidence);

  it("sorts by reported value with missing values last", () => {
    const sorted = sortClaimRows(rows, "reported", -1);
    expect(sorted.map((r) => r.claim.id)).toEqual(["c1", "c3", "c2", "c4"]);
  });

  it("sorts by verdict severity", () => {
    const sorted = sortClaimRows(rows, "verdict", 1);
    expect(sorted.map((r) => r.claim.id)).toEqual(["c1", "c2", "c3", "c4"]);
  });
});
