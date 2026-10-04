import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import UploadDropzone from "./UploadDropzone";

describe("UploadDropzone", () => {
  it("rejects non-PDF files before any upload", () => {
    const onFile = vi.fn();
    render(<UploadDropzone onFile={onFile} uploading={false} />);
    const input = screen.getByLabelText("Choose a paper PDF");
    const txt = new File(["hello"], "notes.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [txt] } });
    expect(screen.getByRole("alert").textContent).toContain(
      "Only PDF files are accepted.",
    );
    expect(onFile).not.toHaveBeenCalled();
  });

  it("accepts a valid PDF", () => {
    const onFile = vi.fn();
    render(<UploadDropzone onFile={onFile} uploading={false} />);
    const input = screen.getByLabelText("Choose a paper PDF");
    const pdf = new File(["%PDF"], "paper.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [pdf] } });
    expect(onFile).toHaveBeenCalledTimes(1);
  });
});
