import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ClaimsList from "./ClaimsList";
import { joinClaimRows } from "../lib/claims";
import type { Claim, Evidence, Verdict } from "../api/models";

const claims: Claim[] = [
  { id: "c4", text: "Generalizes to E", source_ref: "Section 3", reported_value: null },
];
const verdicts: Verdict[] = [
  {
    claim_id: "c4",
    status: "untestable",
    rationale: "No data.",
    evidence_ids: [],
    scaled: false,
    assumption_effects: [],
    reason: "Code audit blocked this claim: no experiment code was produced for c4.",
    code_findings: [
      { rule: "code-present", severity: "blocking", file: "code/c4", line: null, message: "No code.", advisory: false },
    ],
  },
];
const evidence: Evidence[] = [];

describe("verdict reason display", () => {
  it("shows the reason as a short chip next to the untestable badge", () => {
    const rows = joinClaimRows(claims, verdicts, evidence);
    render(<ClaimsList rows={rows} selectedId={null} onSelect={() => {}} />);
    expect(
      screen.getByRole("button", { name: "Claim c4: untestable" }),
    ).toBeDefined();
    expect(
      screen.getByLabelText(/Untestable reason: Code audit blocked/),
    ).toBeDefined();
  });
});
