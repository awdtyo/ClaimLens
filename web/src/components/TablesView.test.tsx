import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TablesView from "./TablesView";
import type { ParsedPaper } from "../api/models";

const parsed: ParsedPaper = {
  title: "Mock paper",
  sections: [],
  tables: [
    {
      id: "t1",
      caption: "Test accuracy.",
      rows: [
        ["Method", "Accuracy (%)"],
        ["X", "91.2"],
      ],
      source: "text",
      page: 2,
    },
    {
      id: "t1",
      caption: "Test accuracy.",
      rows: [
        ["Method", "Accuracy (%)"],
        ["X", "91.3"],
      ],
      source: "vision",
      page: 2,
    },
  ],
  table_mismatches: [
    { table_id: "t1", row: 1, col: 1, text_value: "91.2", vision_value: "91.3" },
  ],
};

describe("TablesView", () => {
  it("flags mismatched cells and shows both values on click", () => {
    render(<TablesView parsed={parsed} />);
    expect(screen.getByText("1 mismatch flagged")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: /Row 2, column 2/ }));
    expect(screen.getAllByText("91.2").length).toBeGreaterThan(0);
    expect(screen.getAllByText("91.3").length).toBeGreaterThan(0);
  });

  it("states the empty case plainly", () => {
    render(<TablesView parsed={{ ...parsed, tables: [] }} />);
    expect(screen.getByText("No tables were extracted from this paper.")).toBeDefined();
  });
});
