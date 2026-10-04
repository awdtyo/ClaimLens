import type { Claim, Evidence, Verdict } from "../api/models";
import { verdictMeta, type VerdictBucket } from "./verdict";

export interface ClaimRow {
  claim: Claim;
  verdict: Verdict | null;
  bucket: VerdictBucket;
  /** Primary measured value: first evidence listed by the backend verdict. */
  measured: number | null;
  primaryEvidence: Evidence | null;
  scaleFactor: number | null;
}

/**
 * Join claims with backend verdicts and measured evidence for display.
 * The primary measurement is the first evidence id the backend lists
 * on the verdict; sensitivity reruns stay attached to the verdict.
 * Nothing here recomputes a verdict.
 */
export function joinClaimRows(
  claims: Claim[],
  verdicts: Verdict[],
  evidence: Evidence[],
): ClaimRow[] {
  const verdictByClaim = new Map(verdicts.map((v) => [v.claim_id, v]));
  const evidenceById = new Map(evidence.map((e) => [e.id, e]));
  return claims.map((claim) => {
    const verdict = verdictByClaim.get(claim.id) ?? null;
    const primaryId = verdict?.evidence_ids?.[0];
    const primaryEvidence = (primaryId ? evidenceById.get(primaryId) : undefined) ?? null;
    return {
      claim,
      verdict,
      bucket: verdictMeta(verdict?.status ?? "untestable").bucket,
      measured: primaryEvidence?.measured_value ?? null,
      primaryEvidence,
      scaleFactor: primaryEvidence?.scale_factor ?? null,
    };
  });
}

export type VerdictCounts = Record<VerdictBucket, number>;

export function countVerdicts(rows: ClaimRow[]): VerdictCounts {
  const counts: VerdictCounts = {
    replicated: 0,
    "partially replicated": 0,
    "not replicated": 0,
    untestable: 0,
  };
  for (const row of rows) counts[row.bucket] += 1;
  return counts;
}

export type ClaimSortKey = "id" | "reported" | "measured" | "verdict";

export interface ClaimFilter {
  bucket: VerdictBucket | "all";
  query: string;
  scaledOnly: boolean;
}

export function filterClaimRows(rows: ClaimRow[], filter: ClaimFilter): ClaimRow[] {
  const q = filter.query.trim().toLowerCase();
  return rows.filter((row) => {
    if (filter.bucket !== "all" && row.bucket !== filter.bucket) return false;
    if (filter.scaledOnly && !(row.verdict?.scaled || (row.scaleFactor ?? 1) < 1)) {
      return false;
    }
    if (q && !`${row.claim.id} ${row.claim.text} ${row.claim.source_ref}`.toLowerCase().includes(q)) {
      return false;
    }
    return true;
  });
}

const BUCKET_RANK: Record<VerdictBucket, number> = {
  replicated: 0,
  "partially replicated": 1,
  "not replicated": 2,
  untestable: 3,
};

export function sortClaimRows(rows: ClaimRow[], key: ClaimSortKey, dir: 1 | -1): ClaimRow[] {
  const value = (row: ClaimRow): number | string => {
    switch (key) {
      case "reported":
        return row.claim.reported_value ?? Number.NaN;
      case "measured":
        return row.measured ?? Number.NaN;
      case "verdict":
        return BUCKET_RANK[row.bucket];
      default:
        return row.claim.id;
    }
  };
  return [...rows].sort((a, b) => {
    const va = value(a);
    const vb = value(b);
    if (typeof va === "number" && typeof vb === "number") {
      if (Number.isNaN(va) && Number.isNaN(vb)) return 0;
      if (Number.isNaN(va)) return 1;
      if (Number.isNaN(vb)) return -1;
      return (va - vb) * dir;
    }
    return String(va).localeCompare(String(vb)) * dir;
  });
}
