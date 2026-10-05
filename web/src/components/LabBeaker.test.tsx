import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LabBeaker from "./LabBeaker";

describe("LabBeaker", () => {
  it("renders the laboratory visual with an accessible description", () => {
    render(<LabBeaker />);
    expect(
      screen.getByLabelText(/Digital laboratory/, { selector: "figure" }),
    ).toBeDefined();
    expect(screen.getByText(/Dataset · WMT 2014/)).toBeDefined();
  });

  it("exposes a text summary for assistive technology", () => {
    render(<LabBeaker />);
    expect(screen.getByText(/releases claim particles into a beaker/)).toBeDefined();
  });
});
