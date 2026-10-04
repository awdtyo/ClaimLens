import { describe, expect, it } from "vitest";

/**
 * End-to-end smoke test against the mock backend
 * (`CLAIMLENS_MOCK_PIPELINE=1 claimlens serve`, default port 8000).
 * Skipped when the backend is not running so `npm test` stays green
 * without a server.
 */
const BASE =
  (import.meta.env.CLAIMLENS_SMOKE_BASE as string | undefined) ??
  "http://localhost:8000";

async function get(path: string): Promise<unknown> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return (await res.json()) as unknown;
}

describe("mock backend smoke", () => {
  it("serves demo runs covering every verdict state", async (ctx) => {
    let demos: unknown;
    try {
      const health = (await get("/api/health")) as { status: string };
      expect(health.status).toBe("ok");
      demos = await get("/api/runs?demo=true");
    } catch {
      ctx.skip();
      return;
    }
    const runs = demos as { run_id: string; status: string }[];
    expect(runs.length).toBeGreaterThan(0);
    const runId = runs[0].run_id;
    const verdicts = (await get(`/api/runs/${runId}/verdicts`)) as {
      status: string;
    }[];
    const statuses = new Set(verdicts.map((v) => v.status));
    for (const expected of [
      "replicated",
      "partially replicated",
      "not replicated",
      "untestable",
    ]) {
      expect(statuses.has(expected)).toBe(true);
    }
    const claims = (await get(`/api/runs/${runId}/claims`)) as unknown[];
    expect(claims.length).toBe(verdicts.length);
  });
});
