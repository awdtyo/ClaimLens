import { describe, expect, it } from "vitest";
import { claimCode, codeFileUrl, codeZipUrl, isBinaryBytes } from "./code";

describe("code api helpers", () => {
  it("builds file URLs by index, never by path", () => {
    expect(codeFileUrl("run1", "c1", 2, 0)).toBe("/api/runs/run1/code/c1/2/0");
    expect(codeFileUrl("run1", "c1", 2, 0)).not.toContain("train.py");
  });

  it("builds the code.zip download URL", () => {
    expect(codeZipUrl("run1")).toBe("/api/runs/run1/code.zip");
  });

  it("detects binary bytes", () => {
    expect(isBinaryBytes(new Uint8Array([104, 105]))).toBe(false);
    expect(isBinaryBytes(new Uint8Array([104, 0, 105]))).toBe(true);
  });

  it("finds one claim in the tree", () => {
    const tree = {
      run_id: "r",
      claims: [{ claim_id: "c1", iterations: [] }],
    } as never;
    expect(claimCode(tree, "c1")?.claim_id).toBe("c1");
    expect(claimCode(tree, "c9")).toBeNull();
    expect(claimCode(null, "c1")).toBeNull();
  });
});
