import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AuditSidebar from "./AuditSidebar";

describe("AuditSidebar", () => {
  it("marks the active section and notifies on selection", () => {
    const onSelect = vi.fn();
    render(<AuditSidebar active="claims" status="done" onSelect={onSelect} />);
    expect(screen.getByRole("button", { name: "Claims" }).getAttribute("aria-current")).toBe("true");
    expect(screen.getByText("Complete")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Evidence" }));
    expect(onSelect).toHaveBeenCalledWith("evidence");
  });
});
