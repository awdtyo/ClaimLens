import { describe, expect, it } from "vitest";
import { diffLines } from "./diff";

describe("diffLines", () => {
  it("marks added and removed lines", () => {
    const rows = diffLines("a\nb\nc", "a\nx\nc");
    expect(rows.map((r) => r.type)).toEqual(["same", "del", "add", "same"]);
    expect(rows[0].text).toBe("a");
  });

  it("returns only same rows for identical files", () => {
    const rows = diffLines("a\nb", "a\nb");
    expect(rows.every((r) => r.type === "same")).toBe(true);
  });
});
