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
    badgeClass:
      "bg-green-100 text-green-800 ring-green-600/20 dark:bg-green-900/40 dark:text-green-200 dark:ring-green-400/20",
    dotClass: "bg-green-600 dark:bg-green-400",
  },
  "partially replicated": {
    bucket: "partially replicated",
    icon: MinusCircle,
    badgeClass:
      "bg-amber-100 text-amber-800 ring-amber-600/20 dark:bg-amber-900/40 dark:text-amber-200 dark:ring-amber-400/20",
    dotClass: "bg-amber-600 dark:bg-amber-400",
  },
  "not replicated": {
    bucket: "not replicated",
    icon: XCircle,
    badgeClass:
      "bg-red-100 text-red-800 ring-red-600/20 dark:bg-red-900/40 dark:text-red-200 dark:ring-red-400/20",
    dotClass: "bg-red-600 dark:bg-red-400",
  },
  untestable: {
    bucket: "untestable",
    icon: CircleDashed,
    badgeClass:
      "bg-gray-100 text-gray-700 ring-gray-500/20 dark:bg-gray-800 dark:text-gray-300 dark:ring-gray-400/20",
    dotClass: "bg-gray-500 dark:bg-gray-400",
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
