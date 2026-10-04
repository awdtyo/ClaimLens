/**
 * Typed API client for the ClaimLens backend.
 *
 * - Types for run data come from the generated OpenAPI types
 *   (`src/api/types.ts`, refreshed with `npm run gen:api`); they are
 *   never hand-written here.
 * - Artifact payloads (`claims`, `verdicts`, …) are typed as `unknown`
 *   by the OpenAPI document, so callers narrow them with the guards in
 *   `src/api/models.ts`.
 * - All URLs are relative (`/api/...`) and go through the Vite dev
 *   proxy; no API URL is hardcoded.
 */
import type { components } from "./types";

export type RunSummary = components["schemas"]["RunSummary"];
export type RunDetail = components["schemas"]["RunDetail"];
export type StageState = components["schemas"]["StageState"];
export type CreateRunResponse =
  components["schemas"]["CreateRunResponse"];

export const STAGE_ORDER = [
  "ingest",
  "claims",
  "plan",
  "sandbox",
  "verify",
  "report",
] as const;

export type StageName = (typeof STAGE_ORDER)[number];

async function checkResponse(res: Response): Promise<Response> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep the status text */
    }
    throw new Error(detail);
  }
  return res;
}

export async function fetchHealth(): Promise<string> {
  const res = await checkResponse(await fetch("/api/health"));
  const data = (await res.json()) as { status: string };
  return data.status;
}

export async function fetchRuns(demo?: boolean): Promise<RunSummary[]> {
  const url = demo === undefined ? "/api/runs" : `/api/runs?demo=${demo}`;
  const res = await checkResponse(await fetch(url));
  return (await res.json()) as RunSummary[];
}

export async function fetchRun(runId: string): Promise<RunDetail> {
  const res = await checkResponse(await fetch(`/api/runs/${runId}`));
  return (await res.json()) as RunDetail;
}

export async function uploadRun(file: File): Promise<CreateRunResponse> {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await checkResponse(
    await fetch("/api/runs", { method: "POST", body: form }),
  );
  return (await res.json()) as CreateRunResponse;
}

export async function cancelRun(runId: string): Promise<RunDetail> {
  const res = await checkResponse(
    await fetch(`/api/runs/${runId}/cancel`, { method: "POST" }),
  );
  return (await res.json()) as RunDetail;
}

/** Fetch a JSON artifact (`claims`, `verdicts`, `evidence`, `plan`, `parsed`). */
export async function fetchArtifact(runId: string, name: string): Promise<unknown> {
  const res = await checkResponse(await fetch(`/api/runs/${runId}/${name}`));
  return (await res.json()) as unknown;
}

/** Fetch the Markdown report as text. */
export async function fetchReport(runId: string): Promise<string> {
  const res = await checkResponse(await fetch(`/api/runs/${runId}/report`));
  return await res.text();
}

/** Relative URL of an artifact (paper PDF, report download). */
export function artifactUrl(runId: string, name: string): string {
  return `/api/runs/${runId}/${name}`;
}
