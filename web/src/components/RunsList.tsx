import { Link } from "react-router-dom";
import type { RunSummary } from "../api/client";
import { formatDateTime } from "../lib/format";
import { cn } from "../lib/utils";
import { Chip, EmptyState, ErrorState, LoadingState } from "./ui";

function statusClass(status: string): string {
  switch (status) {
    case "done":
      return "bg-green-100 text-green-800 ring-green-600/20 dark:bg-green-900/40 dark:text-green-200";
    case "failed":
      return "bg-red-100 text-red-800 ring-red-600/20 dark:bg-red-900/40 dark:text-red-200";
    case "cancelled":
      return "bg-gray-100 text-gray-700 ring-gray-500/20 dark:bg-gray-800 dark:text-gray-300";
    default:
      return "bg-blue-100 text-blue-800 ring-blue-600/20 dark:bg-blue-900/40 dark:text-blue-200";
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
        title="Could not load past runs."
        message="The backend did not answer. Check that the API server is running, then retry."
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
    <ul aria-label="Past runs" className="divide-y divide-gray-200 rounded-lg border border-gray-200 dark:divide-gray-800 dark:border-gray-800">
      {runs.map((run) => (
        <li key={run.run_id}>
          <Link
            to={`/runs/${run.run_id}`}
            className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/50"
          >
            <span className="min-w-0 flex-1 truncate font-medium">
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
              className="text-sm text-gray-600 dark:text-gray-400"
            >
              {formatDateTime(run.created_at)}
            </time>
          </Link>
        </li>
      ))}
    </ul>
  );
}
