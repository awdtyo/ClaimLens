import ReactMarkdown from "react-markdown";
import { Download } from "lucide-react";
import { artifactUrl } from "../api/client";
import { Button, EmptyState, ErrorState, LoadingState } from "./ui";

interface ReportViewProps {
  runId: string;
  report: string | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  /** Backend data bundled for the JSON download (display data only). */
  jsonBundle: Record<string, unknown> | null;
}

/** Download a blob without hardcoding any URL. */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Render the backend Markdown report in-app, with Markdown and JSON
 * downloads. The report text is rendered as-is.
 */
export default function ReportView({
  runId,
  report,
  isLoading,
  isError,
  onRetry,
  jsonBundle,
}: ReportViewProps) {
  if (isLoading) return <LoadingState label="Loading report…" />;
  if (isError) {
    return (
      <ErrorState
        title="Could not load the report."
        message="The report is not ready yet, or the backend did not answer."
        onRetry={onRetry}
      />
    );
  }
  if (!report) {
    return (
      <EmptyState
        title="No report yet."
        hint="The report appears here once the report stage finishes."
      />
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            downloadBlob(new Blob([report], { type: "text/markdown" }), `claimlens-${runId}.md`)
          }
        >
          <Download size={14} aria-hidden="true" /> Download Markdown
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!jsonBundle}
          onClick={() => {
            if (jsonBundle) {
              downloadBlob(
                new Blob([JSON.stringify(jsonBundle, null, 2)], {
                  type: "application/json",
                }),
                `claimlens-${runId}.json`,
              );
            }
          }}
        >
          <Download size={14} aria-hidden="true" /> Download JSON
        </Button>
        <a
          href={artifactUrl(runId, "report")}
          className="inline-flex h-8 items-center rounded-md px-3 text-sm underline"
        >
          Open raw report
        </a>
      </div>
      <article
        aria-label="Verdict report"
        className="prose max-w-none rounded-lg border border-gray-200 p-4 text-sm dark:prose-invert dark:border-gray-800 [&_table]:w-full [&_td]:border [&_td]:border-gray-300 [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-gray-300 [&_th]:bg-gray-50 [&_th]:px-2 [&_th]:py-1 dark:[&_td]:border-gray-700 dark:[&_th]:border-gray-700 dark:[&_th]:bg-gray-800"
      >
        <ReactMarkdown>{report}</ReactMarkdown>
      </article>
    </div>
  );
}
