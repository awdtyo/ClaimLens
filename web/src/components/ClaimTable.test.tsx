import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ClaimTable from "./ClaimTable";
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

describe("ClaimTable", () => {
  it("renders claim rows with reported, reproduced and verdict", () => {
    const rows = joinClaimRows(claims, verdicts, evidence);
    render(<ClaimTable rows={rows} selectedId={null} onSelect={() => {}} />);
    // Both desktop and mobile layouts render (CSS picks the visible one).
    expect(screen.getAllByText("X reaches 91.2% accuracy").length).toBeGreaterThan(0);
    expect(screen.getByRole("row", { name: /Claim c1: replicated/ })).toBeDefined();
  });

  it("marks the selected row and notifies on selection", () => {
    const rows = joinClaimRows(claims, verdicts, evidence);
    const onSelect = vi.fn();
    render(<ClaimTable rows={rows} selectedId="c1" onSelect={onSelect} />);
    expect(screen.getByRole("row", { name: /Claim c1/ }).getAttribute("aria-selected")).toBe("true");
    fireEvent.click(screen.getByRole("row", { name: /Claim c2/ }));
    expect(onSelect).toHaveBeenCalledWith("c2");
  });
});
