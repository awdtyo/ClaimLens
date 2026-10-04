import { VERDICT_ORDER, verdictMeta } from "../lib/verdict";
import type { VerdictCounts } from "../lib/claims";

/**
 * Verdict summary: counts per backend verdict with a bar chart.
 * Text counts accompany the bars so color is not the only signal.
 */
export default function VerdictSummary({ counts }: { counts: VerdictCounts }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  if (total === 0) return null;
  return (
    <div aria-label="Verdict summary" className="flex flex-col gap-2">
      <div
        role="img"
        aria-label={`${counts.replicated} replicated, ${counts["partially replicated"]} partially replicated, ${counts["not replicated"]} not replicated, ${counts.untestable} untestable`}
        className="flex h-4 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800"
      >
        {VERDICT_ORDER.map((bucket) => {
          const n = counts[bucket];
          if (n === 0) return null;
          const meta = verdictMeta(bucket);
          return (
            <div
              key={bucket}
              className={meta.dotClass}
              style={{ width: `${(n / total) * 100}%` }}
            />
          );
        })}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {VERDICT_ORDER.map((bucket) => {
          const meta = verdictMeta(bucket);
          const Icon = meta.icon;
          return (
            <li key={bucket} className="inline-flex items-center gap-1.5">
              <Icon size={14} aria-hidden="true" />
              <span>
                {meta.bucket}: <strong>{counts[bucket]}</strong>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
