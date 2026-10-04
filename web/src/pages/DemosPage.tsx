import { Link } from "react-router-dom";
import { useDemoRuns } from "../hooks/useApi";
import { formatDateTime } from "../lib/format";
import { Card } from "../components/ui";
import RunsList from "../components/RunsList";

/** Gallery of finished demo runs (`demo=true`). */
export default function DemosPage() {
  const demosQuery = useDemoRuns();
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Demo runs</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Finished example audits. Open one to see claims, verdicts, table
          cross-checks and the report.
        </p>
      </div>
      <RunsList
        runs={demosQuery.data}
        isLoading={demosQuery.isLoading}
        isError={demosQuery.isError}
        onRetry={() => void demosQuery.refetch()}
      />
      {demosQuery.data && demosQuery.data.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2">
          {demosQuery.data.map((run) => (
            <Card key={run.run_id} className="p-4">
              <p className="font-medium">{run.filename || run.run_id}</p>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Status: {run.status} · {formatDateTime(run.created_at)}
              </p>
              <Link
                to={`/runs/${run.run_id}`}
                className="mt-2 inline-block text-sm text-blue-700 underline dark:text-blue-300"
              >
                Open results
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
