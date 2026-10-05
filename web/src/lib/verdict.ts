import {
  CheckCircle2,
  CircleDashed,
  MinusCircle,
  XCircle,
  type LucideIcon,
} from "lucide-react";

/**
 * Display metadata for backend verdicts.
 *
 * The frontend displays backend verdicts only: it never computes or
 * changes a verdict (AGENTS.md hard rule). This map only controls how a
 * status string returned by the backend looks. Color is never the only
 * signal: every verdict has an icon and a text label.
 */

export type VerdictBucket =
  | "replicated"
  | "partially replicated"
  | "not replicated"
  | "untestable";

export interface VerdictMeta {
  /** Canonical bucket used for styling and grouping. */
  bucket: VerdictBucket;
  /** Exact status string from the backend, shown as the label. */
  label: string;
  icon: LucideIcon;
  badgeClass: string;
  dotClass: string;
}

const META: Record<VerdictBucket, Omit<VerdictMeta, "label">> = {
  replicated: {
    bucket: "replicated",
    icon: CheckCircle2,
    badgeClass: "bg-[var(--ok-soft)] text-[var(--ok)] ring-[var(--ok)]/20",
    dotClass: "bg-[var(--ok)]",
  },
  "partially replicated": {
    bucket: "partially replicated",
    icon: MinusCircle,
    badgeClass: "bg-[var(--warn-soft)] text-[var(--warn)] ring-[var(--warn)]/20",
    dotClass: "bg-[var(--warn)]",
  },
  "not replicated": {
    bucket: "not replicated",
    icon: XCircle,
    badgeClass: "bg-[var(--bad-soft)] text-[var(--bad)] ring-[var(--bad)]/20",
    dotClass: "bg-[var(--bad)]",
  },
  untestable: {
    bucket: "untestable",
    icon: CircleDashed,
    badgeClass: "bg-[var(--muted-soft)] text-[var(--muted)] ring-[var(--border)]",
    dotClass: "bg-[var(--muted)]",
  },
};

/**
 * Normalize a backend status string to a display bucket.
 * "untestable at this scale" groups with "untestable" but keeps its
 * full label so no information is lost.
 */
export function verdictMeta(status: string): VerdictMeta {
  const lower = status.trim().toLowerCase();
  let bucket: VerdictBucket = "untestable";
  if (lower === "replicated") bucket = "replicated";
  else if (lower === "partially replicated") bucket = "partially replicated";
  else if (lower === "not replicated") bucket = "not replicated";
  return { ...META[bucket], label: status };
}

export const VERDICT_ORDER: VerdictBucket[] = [
  "replicated",
  "partially replicated",
  "not replicated",
  "untestable",
];
