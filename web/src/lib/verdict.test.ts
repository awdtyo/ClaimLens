import { describe, expect, it } from "vitest";
import { verdictMeta } from "./verdict";

describe("verdictMeta", () => {
  it("maps each backend status to its own bucket", () => {
    expect(verdictMeta("replicated").bucket).toBe("replicated");
    expect(verdictMeta("partially replicated").bucket).toBe(
      "partially replicated",
    );
    expect(verdictMeta("not replicated").bucket).toBe("not replicated");
    expect(verdictMeta("untestable").bucket).toBe("untestable");
  });

  it("groups 'untestable at this scale' with untestable but keeps the label", () => {
    const meta = verdictMeta("untestable at this scale");
    expect(meta.bucket).toBe("untestable");
    expect(meta.label).toBe("untestable at this scale");
  });

  it("always provides an icon and a text label", () => {
    for (const status of [
      "replicated",
      "partially replicated",
      "not replicated",
      "untestable",
      "untestable at this scale",
    ]) {
      const meta = verdictMeta(status);
      expect(meta.icon).toBeDefined();
      expect(meta.label).toBe(status);
      expect(meta.badgeClass).toContain("ring-");
    }
  });
});
