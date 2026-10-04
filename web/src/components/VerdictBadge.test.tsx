import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import VerdictBadge from "./VerdictBadge";

describe("VerdictBadge", () => {
  it.each([
    "replicated",
    "partially replicated",
    "not replicated",
    "untestable",
    "untestable at this scale",
  ])("shows an icon and text label for '%s'", (status) => {
    const { container } = render(<VerdictBadge status={status} />);
    expect(screen.getByText(status)).toBeDefined();
    // Icon plus text: color is never the only signal.
    expect(container.querySelector("svg")).not.toBeNull();
  });
});
