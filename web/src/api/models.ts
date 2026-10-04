/**
 * Artifact payload shapes served by `GET /api/runs/{run_id}/{artifact}`.
 *
 * The OpenAPI document types that endpoint as `unknown`, so these
 * interfaces mirror the backend pydantic models in
 * `claimlens/claims/schema.py` (see `docs/CONTRACTS.md`). They describe
 * backend data for display only: the frontend never computes or changes
 * a verdict.
 */

export interface Claim {
  id: string;
  text: string;
  source_ref: string;
  metric?: string | null;
  reported_value?: number | null;
  page?: number | null;
}

export interface Assumption {
  id: string;
  detail: string;
  value_chosen: string;
  reason: string;
  confidence: "low" | "medium" | "high";
}

export interface AssumptionEffect {
  assumption_id: string;
  claim_id: string;
  alt_value: string;
  measured_value?: number | null;
  delta?: number | null;
}

export interface Evidence {
  id: string;
  claim_id: string;
  method: string;
  measured_value?: number | null;
  config?: Record<string, unknown>;
  logs_ref?: string | null;
  scale_factor: number;
}

export interface CodeFinding {
  rule: string;
  severity: "blocking" | "warning" | "info";
  file: string;
  line?: number | null;
  message: string;
  advisory: boolean;
}

export interface Verdict {
  claim_id: string;
  status: string;
  rationale: string;
  evidence_ids: string[];
  scaled: boolean;
  assumption_effects: AssumptionEffect[];
  reason?: string | null;
  code_findings?: CodeFinding[];
}

export type TableRow = string[];

export interface Table {
  id: string;
  caption?: string;
  rows: string[][];
  source: "text" | "vision";
  page?: number | null;
}

export interface TableMismatch {
  table_id: string;
  row: number;
  col: number;
  text_value: string;
  vision_value: string;
}

export interface ParsedPaper {
  title: string;
  sections: { id: string; title: string; text: string; page?: number | null }[];
  tables: Table[];
  table_mismatches: TableMismatch[];
}

export interface PlanItem {
  claim_id: string;
  steps: string[];
  scale_factor: number;
  config?: Record<string, unknown>;
}

export interface Plan {
  items: PlanItem[];
  assumptions: Assumption[];
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

/** Lenient runtime guards: malformed artifacts render an error state. */
export function parseClaims(data: unknown): Claim[] | null {
  if (!Array.isArray(data)) return null;
  if (!data.every((c) => isRecord(c) && typeof c["id"] === "string")) return null;
  return data as Claim[];
}

export function parseVerdicts(data: unknown): Verdict[] | null {
  if (!Array.isArray(data)) return null;
  if (
    !data.every((v) => isRecord(v) && typeof v["claim_id"] === "string")
  ) {
    return null;
  }
  return data as Verdict[];
}

export function parseEvidence(data: unknown): Evidence[] | null {
  if (!Array.isArray(data)) return null;
  if (!data.every((e) => isRecord(e) && typeof e["id"] === "string")) return null;
  return data as Evidence[];
}

export function parsePlan(data: unknown): Plan | null {
  if (!isRecord(data)) return null;
  if (!Array.isArray(data["items"]) || !Array.isArray(data["assumptions"])) {
    return null;
  }
  return data as unknown as Plan;
}

export function parseParsedPaper(data: unknown): ParsedPaper | null {
  if (!isRecord(data) || typeof data["title"] !== "string") return null;
  return {
    title: data["title"],
    sections: asArray(data["sections"]).filter(isRecord) as ParsedPaper["sections"],
    tables: asArray(data["tables"]).filter(isRecord) as unknown as Table[],
    table_mismatches: asArray(data["table_mismatches"]).filter(
      isRecord,
    ) as unknown as TableMismatch[],
  };
}
