import type { CodeFinding } from "../api/models";
import { findingFileName, groupFindingsBySeverity, isBlockingFinding, severityMeta } from "../lib/findings";
import { cn } from "../lib/utils";
import { EmptyState } from "./ui";

interface FindingsListProps {
  findings: CodeFinding[];
  verdictStatus: string;
  onOpenFile: (file: string, line: number | null) => void;
}

/**
 * Code findings grouped by severity. Blocking deterministic findings are
 * prominent and explain why the verdict is untestable; advisory
 * findings are labeled advisory and shown at lower priority. Display
 * only: never changes the backend verdict.
 */
export default function FindingsList({ findings, verdictStatus, onOpenFile }: FindingsListProps) {
  if (!findings || findings.length === 0) {
    return (
      <EmptyState
        title="No code findings."
        hint="The code audit reported no issues for this claim."
      />
    );
  }
  const grouped = groupFindingsBySeverity(findings);
  const hasBlocking = grouped.blocking.some((f) => !f.advisory);
  return (
    <div className="flex flex-col gap-4">
      {hasBlocking && (
        <div
          role="note"
          aria-label="Blocking findings"
          className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-200"
        >
          <p className="font-medium">Blocking findings: this claim is untestable.</p>
          <p className="mt-1">
            Deterministic code checks found a problem, so the backend set the
            verdict to “{verdictStatus}” instead of a replication outcome.
          </p>
        </div>
      )}
      {(["blocking", "warning", "info"] as const).map((severity) => {
        const items = grouped[severity];
        if (items.length === 0) return null;
        const meta = severityMeta(severity);
        const Icon = meta.icon;
        return (
          <section key={severity} aria-label={`${severity} findings`}>
            <h4 className="mb-2 flex items-center gap-1.5 text-sm font-medium">
              <Icon size={14} aria-hidden="true" />
              <span className="capitalize">{severity}</span>
              <span className="text-gray-500">({items.length})</span>
            </h4>
            <ul className="flex flex-col gap-2">
              {items.map((finding, i) => {
                const blocking = isBlockingFinding(finding);
                const advisory = finding.advisory;
                return (
                  <li
                    key={`${finding.rule}-${i}`}
                    className={cn(
                      "rounded-lg border p-3",
                      blocking
                        ? "border-red-300 bg-red-50/50 dark:border-red-800 dark:bg-red-950/30"
                        : "border-gray-200 dark:border-gray-800",
                      advisory && "opacity-90",
                    )}
                  >
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium ring-1 ring-inset",
                          meta.badgeClass,
                        )}
                      >
                        <Icon size={12} aria-hidden="true" />
                        <span>{severity}</span>
                      </span>
                      {advisory ? (
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-600 ring-1 ring-inset ring-gray-500/20 dark:bg-gray-800 dark:text-gray-300">
                          advisory: does not change the verdict
                        </span>
                      ) : (
                        <span className="rounded-full bg-gray-900 px-2 py-0.5 text-white dark:bg-gray-100 dark:text-gray-900">
                          deterministic
                        </span>
                      )}
                      <span className="font-mono text-gray-500">{finding.rule}</span>
                    </div>
                    <p className="mt-1.5 text-sm">{finding.message}</p>
                    <button
                      type="button"
                      onClick={() => onOpenFile(finding.file, finding.line ?? null)}
                      aria-label={`Open ${finding.file}${finding.line != null ? ` at line ${finding.line}` : ""} in the Code tab`}
                      className="mt-1.5 font-mono text-xs text-blue-700 underline hover:text-blue-900 dark:text-blue-300 dark:hover:text-blue-100"
                    >
                      {findingFileName(finding.file)}
                      {finding.line != null && `:${finding.line}`}
                      <span className="ml-1 font-sans text-gray-500 no-underline">
                        ({finding.file})
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
