import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import FindingsList from "./FindingsList";
import type { CodeFinding } from "../api/models";

const findings: CodeFinding[] = [
  { rule: "code-present", severity: "blocking", file: "code/c4", line: null, message: "No experiment code was produced.", advisory: false },
  { rule: "llm-seed-review", severity: "warning", file: "code/c1/iter_1/train.py", line: 14, message: "No seed fixed.", advisory: true },
];

describe("FindingsList", () => {
  it("shows blocking findings prominently and advisory as advisory", () => {
    render(<FindingsList findings={findings} verdictStatus="untestable" onOpenFile={() => {}} />);
    expect(screen.getByText(/blocking findings/i)).toBeDefined();
    expect(screen.getByText(/advisory: does not change the verdict/i)).toBeDefined();
    expect(screen.getByText("deterministic")).toBeDefined();
  });

  it("shows an empty state with no findings", () => {
    render(<FindingsList findings={[]} verdictStatus="replicated" onOpenFile={() => {}} />);
    expect(screen.getByText("No code findings.")).toBeDefined();
  });

  it("links each finding to its file and line", () => {
    const onOpenFile = vi.fn();
    render(<FindingsList findings={findings} verdictStatus="untestable" onOpenFile={onOpenFile} />);
    fireEvent.click(screen.getByRole("button", { name: /train\.py at line 14/ }));
    expect(onOpenFile).toHaveBeenCalledWith("code/c1/iter_1/train.py", 14);
  });
});
