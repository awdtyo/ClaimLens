import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RunDetail } from "../api/client";
import PipelineStepper from "./PipelineStepper";

function makeRun(stages: Record<string, { status: string }>): RunDetail {
  return {
    run_id: "abc",
    status: "running",
    demo: false,
    filename: "paper.pdf",
    created_at: "",
    updated_at: "",
    stages: stages as RunDetail["stages"],
  };
}

describe("PipelineStepper", () => {
  it("builds the stepper from the API run state including code_audit", () => {
    const run = makeRun({
      ingest: { status: "done" },
      claims: { status: "done" },
      plan: { status: "done" },
      sandbox: { status: "done" },
      code_audit: { status: "running" },
      verify: { status: "pending" },
      report: { status: "pending" },
    });
    render(<PipelineStepper run={run} />);
    expect(screen.getByText(/code audit/i)).toBeDefined();
  });

  it("renders unknown future stages with a generic label instead of breaking", () => {
    const run = makeRun({
      ingest: { status: "done" },
      claims: { status: "done" },
      future_stage_x: { status: "running" },
    });
    render(<PipelineStepper run={run} />);
    // Underscores become spaces; the raw stage is still shown generically.
    expect(screen.getByText(/future stage x/i)).toBeDefined();
    expect(screen.getByText(/ingest/i)).toBeDefined();
  });
});
