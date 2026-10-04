import { describe, expect, it } from "vitest";
import type { CodeFinding } from "../api/models";
import { groupFindingsBySeverity, isBlockingFinding, shortReason } from "./findings";

const findings: CodeFinding[] = [
  { rule: "code-present", severity: "blocking", file: "code/c4", line: null, message: "No code.", advisory: false },
  { rule: "llm-seed-review", severity: "warning", file: "code/c1/iter_1/train.py", line: 14, message: "No seed.", advisory: true },
  { rule: "style", severity: "info", file: "code/c1/iter_1/train.py", line: 1, message: "Note.", advisory: true },
];

describe("groupFindingsBySeverity", () => {
  it("groups by severity", () => {
    const grouped = groupFindingsBySeverity(findings);
    expect(grouped.blocking).toHaveLength(1);
    expect(grouped.warning).toHaveLength(1);
    expect(grouped.info).toHaveLength(1);
  });

  it("marks only deterministic blocking findings as blocking", () => {
    expect(isBlockingFinding(findings[0])).toBe(true);
    expect(isBlockingFinding(findings[1])).toBe(false);
    expect(
      isBlockingFinding({ ...findings[0], advisory: true }),
    ).toBe(false);
  });
});

describe("shortReason", () => {
  it("returns null for empty reasons", () => {
    expect(shortReason(null)).toBeNull();
    expect(shortReason("  ")).toBeNull();
  });

  it("truncates long reasons", () => {
    expect(shortReason("a".repeat(100), 80)?.length).toBeLessThanOrEqual(80);
    expect(shortReason("short")).toBe("short");
  });
});
