import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CodeTab from "./CodeTab";

function renderTab(props: Partial<React.ComponentProps<typeof CodeTab>> = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CodeTab
        runId="run1"
        claimId="c1"
        codeClaim={null}
        treeLoading={false}
        treeError={false}
        onRetryTree={() => {}}
        runFailed={false}
        {...props}
      />
    </QueryClientProvider>,
  );
}

describe("CodeTab states", () => {
  it("shows a no-code-yet state for claims that have not started", () => {
    renderTab({ codeClaim: null, runFailed: false });
    expect(screen.getByText("No code yet.")).toBeDefined();
  });

  it("explains a failed run with no saved code", () => {
    renderTab({ codeClaim: null, runFailed: true });
    expect(screen.getByText("Run failed before code was written.")).toBeDefined();
  });

  it("shows a loading state while the tree loads", () => {
    renderTab({ treeLoading: true });
    expect(screen.getByText("Loading code…")).toBeDefined();
  });

  it("shows an error state with retry when the tree fails", () => {
    renderTab({ treeError: true });
    expect(screen.getByText("Could not load code.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Retry" })).toBeDefined();
  });

  it("exposes the file tree with tree roles for keyboard users", () => {
    renderTab({
      codeClaim: {
        claim_id: "c1",
        iterations: [{ iteration: 1, files: [{ index: 0, name: "train.py", size: 100 }] }],
      },
    });
    expect(screen.getByRole("tree", { name: /Files in iteration 1/ })).toBeDefined();
    expect(screen.getByRole("treeitem", { name: /train\.py/ })).toBeDefined();
  });
});
