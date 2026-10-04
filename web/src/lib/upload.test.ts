import { describe, expect, it } from "vitest";
import { checkUploadFile, MAX_UPLOAD_BYTES } from "./upload";

function pdf(name: string, size: number, type = "application/pdf"): File {
  const bytes = new Uint8Array(size);
  return new File([bytes], name, { type });
}

describe("checkUploadFile", () => {
  it("accepts a small PDF", () => {
    expect(checkUploadFile(pdf("paper.pdf", 100))).toEqual({ ok: true });
  });

  it("rejects non-PDF files", () => {
    const txt = new File(["hello"], "paper.txt", { type: "text/plain" });
    expect(checkUploadFile(txt)).toEqual({ ok: false, error: "not-pdf" });
  });

  it("rejects files over 30 MB", () => {
    expect(checkUploadFile(pdf("big.pdf", MAX_UPLOAD_BYTES + 1))).toEqual({
      ok: false,
      error: "too-large",
    });
  });

  it("rejects missing or empty files", () => {
    expect(checkUploadFile(null)).toEqual({ ok: false, error: "empty" });
    expect(checkUploadFile(undefined)).toEqual({ ok: false, error: "empty" });
  });
});
