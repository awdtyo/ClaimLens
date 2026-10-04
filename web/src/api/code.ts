/**
 * Generated-code API helpers.
 *
 * The file tree comes from `GET /api/runs/{id}/code` (typed by
 * `src/api/types.ts`, refreshed with `npm run gen:api`). File content is
 * fetched on demand by server-assigned file index through
 * `GET /api/runs/{id}/code/{claimId}/{iteration}/{fileIndex}` — paths are
 * never constructed client-side.
 *
 * `code.zip` (`GET /api/runs/{id}/code.zip`) is the documented download
 * endpoint. The current `docs/openapi.json` does not yet describe it
 * (see PR notes); the frontend links to it by convention and shows an
 * error state when the backend does not serve it.
 */
import type { components } from "./types";

export type CodeTree = components["schemas"]["CodeTree"];
export type CodeClaim = components["schemas"]["CodeClaim"];
export type CodeIteration = components["schemas"]["CodeIteration"];
export type CodeFile = components["schemas"]["CodeFile"];

/** Files larger than this are truncated in the viewer with a warning. */
export const MAX_VIEW_BYTES = 200_000;
/** Maximum lines shown before truncation. */
export const MAX_VIEW_LINES = 2000;

export interface CodeFileContent {
  text: string;
  truncated: boolean;
  binary: boolean;
  size: number;
}

export function codeFileUrl(
  runId: string,
  claimId: string,
  iteration: number,
  fileIndex: number,
): string {
  return `/api/runs/${runId}/code/${claimId}/${iteration}/${fileIndex}`;
}

/** Download URL for the whole run's generated code (spec endpoint). */
export function codeZipUrl(runId: string): string {
  return `/api/runs/${runId}/code.zip`;
}

export async function fetchCodeTree(runId: string): Promise<CodeTree> {
  const res = await fetch(`/api/runs/${runId}/code`);
  if (!res.ok) {
    throw new Error(`Could not load code tree (HTTP ${res.status}).`);
  }
  return (await res.json()) as CodeTree;
}

/** Find one claim's entry in the code tree. */
export function claimCode(
  tree: CodeTree | null | undefined,
  claimId: string,
): CodeClaim | null {
  if (!tree) return null;
  return tree.claims.find((c) => c.claim_id === claimId) ?? null;
}

/** Detect binary content from raw bytes (null byte or mostly non-text). */
export function isBinaryBytes(bytes: Uint8Array): boolean {
  const sample = bytes.slice(0, 8000);
  if (sample.length === 0) return false;
  let nonText = 0;
  for (let i = 0; i < sample.length; i += 1) {
    const b = sample[i];
    if (b === 0) return true;
    if (b < 9 || (b > 13 && b < 32 && b !== 27)) nonText += 1;
  }
  return nonText / sample.length > 0.3;
}

/**
 * Fetch one code file by server-assigned index. Binary files are
 * reported as non-viewable; very large files are truncated with a flag.
 */
export async function fetchCodeFile(
  runId: string,
  claimId: string,
  iteration: number,
  fileIndex: number,
): Promise<CodeFileContent> {
  const res = await fetch(codeFileUrl(runId, claimId, iteration, fileIndex));
  if (!res.ok) {
    throw new Error(`Could not load code file (HTTP ${res.status}).`);
  }
  const buffer = await res.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  if (isBinaryBytes(bytes)) {
    return { text: "", truncated: false, binary: true, size: bytes.length };
  }
  let text = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
  // Strip a stray null that survived sampling (belt and braces).
  if (text.includes("\u0000")) {
    return { text: "", truncated: false, binary: true, size: bytes.length };
  }
  let truncated = false;
  if (bytes.length > MAX_VIEW_BYTES) {
    text = new TextDecoder("utf-8", { fatal: false }).decode(
      bytes.slice(0, MAX_VIEW_BYTES),
    );
    truncated = true;
  }
  const lines = text.split("\n");
  if (!truncated && lines.length > MAX_VIEW_LINES) {
    text = lines.slice(0, MAX_VIEW_LINES).join("\n");
    truncated = true;
  }
  return { text, truncated, binary: false, size: bytes.length };
}
