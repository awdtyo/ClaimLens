import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App.tsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("shows the backend health through the Vite proxy", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: "ok" }),
      }),
    );
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId("health").textContent).toBe("ok");
    });
    expect(fetch).toHaveBeenCalledWith("/api/health");
  });
});
