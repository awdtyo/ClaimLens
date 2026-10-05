import { Link } from "react-router-dom";
import type { RunSummary } from "../api/client";
import { formatDateTime } from "../lib/format";
import { cn } from "../lib/utils";
import { Chip, EmptyState, ErrorState, LoadingState } from "./ui";

function statusClass(status: string): string {
  switch (status) {
    case "done":
      return "bg-[var(--ok-soft)] text-[var(--ok)] ring-[var(--ok)]/20";
    case "failed":
      return "bg-[var(--bad-soft)] text-[var(--bad)] ring-[var(--bad)]/20";
    case "cancelled":
      return "bg-[var(--muted-soft)] text-[var(--muted)] ring-[var(--border)]";
    default:
      return "bg-[var(--accent-2-soft)] text-[var(--accent-2)] ring-[var(--accent-2)]/20";
  }
}

/** List of past runs with status and date. */
export default function RunsList({
  runs,
  isLoading,
  isError,
  onRetry,
}: {
  runs: RunSummary[] | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}) {
  if (isLoading) return <LoadingState label="Loading past runs…" />;
  if (isError) {
    return (
      <ErrorState
        title="Unable to connect to audit server"
        message="Check your connection and retry."
        onRetry={onRetry}
      />
    );
  }
  if (!runs || runs.length === 0) {
    return (
      <EmptyState
        title="No runs yet."
        hint="Upload a paper PDF above to start the first audit, or try the demo run."
      />
    );
  }
  return (
    <ul aria-label="Past runs" className="cl-surface divide-y divide-[var(--border)] overflow-hidden !p-0">
      {runs.map((run) => (
        <li key={run.run_id}>
          <Link
            to={`/runs/${run.run_id}`}
            className="cl-lift flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3"
          >
            <span className="min-w-0 flex-1 truncate text-[0.9375rem] font-medium">
              {run.filename || run.run_id}
            </span>
            {run.demo && <Chip>demo</Chip>}
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
                statusClass(run.status),
              )}
            >
              {run.status}
            </span>
            <time
              dateTime={run.created_at}
              className="cl-meta"
            >
              {formatDateTime(run.created_at)}
            </time>
            <span aria-hidden="true" className="text-[var(--text-2)]">→</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
