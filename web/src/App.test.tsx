import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App.tsx";
import { ThemeProvider } from "./hooks/useTheme.tsx";

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("shows the upload dropzone, demo button and past runs", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (String(url).includes("/api/runs")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve([]),
          });
        }
        return Promise.reject(new Error(`unexpected ${url}`));
      }),
    );
    renderApp();
    expect(screen.getByLabelText("Upload a paper PDF")).toBeDefined();
    expect(screen.getByRole("button", { name: "Try the demo run" })).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText("No runs yet.")).toBeDefined();
    });
  });

  it("navigates to demos and about pages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      }),
    );
    renderApp();
    screen.getByRole("link", { name: "About" }).click();
    await waitFor(() => {
      expect(screen.getByText("The scaled-run rule")).toBeDefined();
    });
  });
});
