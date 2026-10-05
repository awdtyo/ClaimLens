import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";
import { artifactUrl, fetchRuns, uploadRun } from "../api/client";
import { useRuns } from "../hooks/useApi";
import { HOW_IT_WORKS } from "../lib/site";
import { Button, Card, ErrorState } from "../components/ui";
import RunsList from "../components/RunsList";
import UploadDropzone from "../components/UploadDropzone";

/**
 * Home page: hero, upload, demo entry point, workflow, past runs.
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
    <div className="flex flex-col gap-10">
      {/* Hero */}
      <section aria-labelledby="hero-heading" className="flex flex-col gap-5 pt-4 md:flex-row md:items-center md:gap-10 md:pt-8">
        <div className="flex max-w-xl flex-col gap-3">
          <p className="cl-meta font-medium uppercase tracking-[0.12em]">Research integrity tooling</p>
          <h1 id="hero-heading" className="cl-hero">
            Audit Research Claims. Reproduce the Evidence.
          </h1>
          <p className="cl-body text-[var(--text-2)]">
            Upload a research paper and ClaimLens extracts testable claims,
            reproduces key experiments in a sandbox, and generates
            evidence-backed verdicts.
          </p>
          <div className="mt-1 flex flex-wrap gap-2">
            <Button onClick={() => document.getElementById("upload-heading")?.scrollIntoView({ behavior: "smooth" })}>
              Upload Research Paper
            </Button>
            <Button variant="outline" onClick={() => void startDemo()} disabled={demoLoading}>
              {demoLoading ? "Starting demo…" : "Run Interactive Demo"}
            </Button>
          </div>
          {demoError && (
            <p role="alert" className="text-sm text-[var(--bad)]">
              {demoError}
            </p>
          )}
        </div>
        <div aria-hidden="true" className="cl-surface hidden flex-1 flex-col gap-2 p-5 md:flex">
          <div className="flex items-center gap-2 text-[var(--text-2)]">
            <FileText size={16} />
            <span className="cl-mono text-xs">paper.pdf → claims.json → verdicts</span>
          </div>
          <div className="cl-surface-2 flex flex-col gap-1.5 p-3 font-mono text-xs">
            <p><span className="text-[var(--ok)]">✓</span> claim c1 … replicated (91.1 vs 91.2)</p>
            <p><span className="text-[var(--warn)]">~</span> claim c2 … partially replicated (scaled)</p>
            <p><span className="text-[var(--muted)]">○</span> claim c4 … untestable (no data)</p>
          </div>
          <p className="cl-meta">One tasteful preview of a finished audit.</p>
        </div>
      </section>

      {/* Upload */}
      <section aria-labelledby="upload-heading" className="flex flex-col gap-3">
        <div>
          <h2 id="upload-heading" className="cl-h2">
            Start an audit
          </h2>
          <p className="cl-meta mt-0.5">
            Drag &amp; drop your PDF here or browse files. PDF · Up to 30 MB.
          </p>
        </div>
        <Card>
          <UploadDropzone
            uploading={uploadMutation.isPending}
            error={uploadError}
            onFile={(file) => uploadMutation.mutate(file)}
          />
          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-[var(--border)] pt-4">
            <span className="cl-meta">Don&apos;t have a paper?</span>
            <Button
              variant="outline"
              disabled={demoLoading || uploadMutation.isPending}
              onClick={() => void startDemo()}
            >
              {demoLoading ? "Starting demo…" : "Try the demo run"}
            </Button>
            <Link to="/demos" className="cl-meta underline underline-offset-4">
              Browse demo audits
            </Link>
          </div>
        </Card>
      </section>

      {/* How it works */}
      <section aria-labelledby="how-heading" id="how-it-works" className="flex scroll-mt-20 flex-col gap-4">
        <div>
          <p className="cl-meta font-medium uppercase tracking-[0.12em]">How ClaimLens works</p>
          <h2 id="how-heading" className="cl-h1 mt-1">
            From paper to verdict in four steps
          </h2>
        </div>
        <ol className="cl-timeline-line relative grid gap-4 md:grid-cols-4">
          {HOW_IT_WORKS.map((step) => (
            <li key={step.n} className="cl-surface cl-lift relative flex flex-col gap-1 p-4 pl-12 md:pl-4 md:pt-12">
              <span
                aria-hidden="true"
                className="absolute left-4 top-4 flex h-10 w-10 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface-2)] font-mono text-xs text-[var(--text-2)] md:left-4 md:top-4"
              >
                {step.n}
              </span>
              <p className="text-[0.9375rem] font-semibold">{step.title}</p>
              <p className="cl-meta">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Past audits */}
      <section aria-labelledby="runs-heading" id="audits" className="flex scroll-mt-20 flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="runs-heading" className="cl-h1">
            Past audits
          </h2>
          <Link to="/demos" className="cl-meta underline underline-offset-4">
            View demo audits
          </Link>
        </div>
        {runsQuery.isError && !runsQuery.isLoading ? (
          <ErrorState
            title="Unable to connect to audit server"
            message="Check your connection and retry."
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

      {/* Integrity note */}
      <aside aria-label="Research integrity" className="cl-surface-2 flex flex-col gap-1 p-4">
        <p className="text-sm font-semibold">Research Integrity</p>
        <p className="cl-meta max-w-3xl">
          ClaimLens performs reduced-scale reproduction experiments. A failed
          reproduction does not automatically prove that the original paper is
          incorrect.
        </p>
      </aside>
    </div>
  );
}
