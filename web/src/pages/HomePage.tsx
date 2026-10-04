import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { artifactUrl, fetchRuns, uploadRun } from "../api/client";
import { useRuns } from "../hooks/useApi";
import { Button, Card, ErrorState } from "../components/ui";
import RunsList from "../components/RunsList";
import UploadDropzone from "../components/UploadDropzone";

/**
 * Home page: upload, demo entry point, past runs.
 */
export default function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const runsQuery = useRuns();
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: uploadRun,
    onSuccess: (data) => {
      setUploadError(null);
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void navigate(`/runs/${data.run_id}`);
    },
    onError: (err) => {
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    },
  });

  /**
   * "Try the demo run": re-upload the paper of a finished demo run so
   * the visitor watches a live pipeline. Falls back to the demo
   * gallery when no demo paper is available.
   */
  const startDemo = async () => {
    setDemoLoading(true);
    setDemoError(null);
    try {
      const demos = await fetchRuns(true);
      const demo = demos.find((d) => d.status === "done") ?? demos[0];
      if (!demo) {
        void navigate("/demos");
        return;
      }
      const res = await fetch(artifactUrl(demo.run_id, "paper"));
      if (!res.ok) throw new Error(`Could not fetch the demo paper (HTTP ${res.status}).`);
      const blob = await res.blob();
      const file = new File([blob], demo.filename || "demo-paper.pdf", {
        type: "application/pdf",
      });
      const created = await uploadRun(file);
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void navigate(`/runs/${created.run_id}`);
    } catch (err) {
      setDemoError(err instanceof Error ? err.message : "Could not start the demo run.");
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="upload-heading" className="flex flex-col gap-3">
        <div>
          <h1 id="upload-heading" className="text-2xl font-semibold tracking-tight">
            Audit a paper, claim by claim
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Upload a paper PDF. ClaimLens extracts testable claims, runs
            reduced-scale reproductions in a sandbox, and reports a
            backend-computed verdict for each claim.
          </p>
        </div>
        <Card className="p-4">
          <UploadDropzone
            uploading={uploadMutation.isPending}
            error={uploadError}
            onFile={(file) => uploadMutation.mutate(file)}
          />
          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-gray-200 pt-4 dark:border-gray-800">
            <Button
              variant="outline"
              disabled={demoLoading || uploadMutation.isPending}
              onClick={() => void startDemo()}
            >
              {demoLoading ? "Starting demo…" : "Try the demo run"}
            </Button>
            {demoError && (
              <p role="alert" className="text-sm text-red-700 dark:text-red-300">
                {demoError}
              </p>
            )}
          </div>
        </Card>
      </section>

      <section aria-labelledby="runs-heading" className="flex flex-col gap-3">
        <h2 id="runs-heading" className="text-lg font-semibold">
          Past runs
        </h2>
        {runsQuery.isError && !runsQuery.isLoading ? (
          <ErrorState
            title="Could not load past runs."
            message="The backend did not answer. Check that the API server is running, then retry."
            onRetry={() => void runsQuery.refetch()}
          />
        ) : (
          <RunsList
            runs={runsQuery.data}
            isLoading={runsQuery.isLoading}
            isError={false}
            onRetry={() => void runsQuery.refetch()}
          />
        )}
      </section>
    </div>
  );
}
