import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ClaimsList from "./ClaimsList";
import { joinClaimRows } from "../lib/claims";
import type { Claim, Evidence, Verdict } from "../api/models";

const claims: Claim[] = [
  { id: "c1", text: "X reaches 91.2% accuracy", source_ref: "Table 1", reported_value: 91.2 },
  { id: "c2", text: "Trains faster", source_ref: "Section 4", reported_value: 2.0 },
];
const verdicts: Verdict[] = [
  { claim_id: "c1", status: "replicated", rationale: "", evidence_ids: ["e1"], scaled: false, assumption_effects: [] },
  { claim_id: "c2", status: "partially replicated", rationale: "", evidence_ids: ["e2"], scaled: true, assumption_effects: [] },
];
const evidence: Evidence[] = [
  { id: "e1", claim_id: "c1", method: "m", measured_value: 91.1, scale_factor: 1.0 },
  { id: "e2", claim_id: "c2", method: "m", measured_value: 1.7, scale_factor: 0.1 },
];

describe("ClaimsList", () => {
  it("renders claim text with verdict badges, values and scale chips", () => {
    const rows = joinClaimRows(claims, verdicts, evidence);
    render(<ClaimsList rows={rows} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText("X reaches 91.2% accuracy")).toBeDefined();
    // Badge text also appears in the verdict <select>; the claim button
    // label pins the verdict to the claim.
    expect(
      screen.getByRole("button", { name: "Claim c1: replicated" }),
    ).toBeDefined();
    expect(screen.getByText("scale ×0.1")).toBeDefined();
  });

  it("filters by verdict and notifies on selection", () => {
    const rows = joinClaimRows(claims, verdicts, evidence);
    const onSelect = vi.fn();
    render(<ClaimsList rows={rows} selectedId={null} onSelect={onSelect} />);
    fireEvent.change(screen.getByLabelText("Filter by verdict"), {
      target: { value: "replicated" },
    });
    expect(screen.queryByText("Trains faster")).toBeNull();
    expect(screen.getByText("X reaches 91.2% accuracy")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: /Claim c1/ }));
    expect(onSelect).toHaveBeenCalledWith("c1");
  });
});
