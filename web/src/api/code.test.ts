import { describe, expect, it } from "vitest";
import { claimCode, codeFileUrl, codeTreeKeys, codeZipUrl, isBinaryBytes, isCodeWrittenEvent } from "./code";

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

  it("detects code_written events including mock sandbox lines", () => {
    expect(isCodeWrittenEvent({ stage: "code_written", status: "progress" } as never)).toBe(true);
    expect(
      isCodeWrittenEvent({ stage: "sandbox", message: "agent: wrote train_x.py" } as never),
    ).toBe(true);
    expect(
      isCodeWrittenEvent({ stage: "sandbox", message: "agent: epoch 10/10 loss 0.31" } as never),
    ).toBe(false);
    expect(isCodeWrittenEvent({ stage: "verify", message: "comparing numbers" } as never)).toBe(false);
  });

  it("lists stable file keys for new-file detection", () => {
    const tree = {
      run_id: "r",
      claims: [
        { claim_id: "c1", iterations: [{ iteration: 1, files: [{ index: 0, name: "train.py", size: 10 }] }] },
      ],
    } as never;
    expect(codeTreeKeys(tree).has("c1/1/train.py")).toBe(true);
    expect(codeTreeKeys(null).size).toBe(0);
  });
});
