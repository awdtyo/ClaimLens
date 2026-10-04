import { AlertOctagon, AlertTriangle, Info, type LucideIcon } from "lucide-react";
import type { CodeFinding } from "../api/models";

/**
 * Code-finding helpers. Grouping and labels are display only: the
 * backend verdict (including `reason` for blocking findings) is shown
 * as-is and never recomputed here.
 */

export type FindingSeverity = "blocking" | "warning" | "info";

export interface GroupedFindings {
  blocking: CodeFinding[];
  warning: CodeFinding[];
  info: CodeFinding[];
}

/** Group findings by severity; unknown severities fall back to info. */
export function groupFindingsBySeverity(findings: CodeFinding[]): GroupedFindings {
  const grouped: GroupedFindings = { blocking: [], warning: [], info: [] };
  for (const f of findings ?? []) {
    if (f.severity === "blocking") grouped.blocking.push(f);
    else if (f.severity === "warning") grouped.warning.push(f);
    else grouped.info.push(f);
  }
  return grouped;
}

/** A finding blocks the verdict only when deterministic (advisory=false). */
export function isBlockingFinding(finding: CodeFinding): boolean {
  return finding.severity === "blocking" && finding.advisory === false;
}

export interface SeverityMeta {
  icon: LucideIcon;
  label: string;
  badgeClass: string;
}

const SEVERITY_META: Record<FindingSeverity, SeverityMeta> = {
  blocking: {
    icon: AlertOctagon,
    label: "blocking",
    badgeClass:
      "bg-red-100 text-red-800 ring-red-600/20 dark:bg-red-900/40 dark:text-red-200 dark:ring-red-400/20",
  },
  warning: {
    icon: AlertTriangle,
    label: "warning",
    badgeClass:
      "bg-amber-100 text-amber-800 ring-amber-600/20 dark:bg-amber-900/40 dark:text-amber-200 dark:ring-amber-400/20",
  },
  info: {
    icon: Info,
    label: "info",
    badgeClass:
      "bg-gray-100 text-gray-700 ring-gray-500/20 dark:bg-gray-800 dark:text-gray-300 dark:ring-gray-400/20",
  },
};

export function severityMeta(severity: string): SeverityMeta {
  if (severity === "blocking") return SEVERITY_META.blocking;
  if (severity === "warning") return SEVERITY_META.warning;
  return SEVERITY_META.info;
}

/** Short chip text for a verdict reason (full text kept in title). */
export function shortReason(reason: string | null | undefined, max = 80): string | null {
  if (!reason) return null;
  const trimmed = reason.trim();
  if (trimmed.length === 0) return null;
  return trimmed.length > max ? `${trimmed.slice(0, max - 1)}…` : trimmed;
}

/** File name shown for a finding (last path segment). */
export function findingFileName(file: string): string {
  const parts = file.split("/").filter(Boolean);
  return parts.length > 0 ? parts[parts.length - 1] : file;
}
