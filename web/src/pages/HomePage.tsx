import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Database, FlaskConical, GitBranch, Microscope, Scale, FileText } from "lucide-react";
import { artifactUrl, fetchRuns, uploadRun } from "../api/client";
import { useRuns } from "../hooks/useApi";
import { useReveal } from "../lib/reveal";
import { Button, Card, ErrorState } from "../components/ui";
import LabBeaker from "../components/LabBeaker";
import RunsList from "../components/RunsList";
import UploadDropzone from "../components/UploadDropzone";
import VerdictBadge from "../components/VerdictBadge";

const PIPELINE = [
  { icon: FileText, label: "Paper", text: "Published research" },
  { icon: GitBranch, label: "Claims", text: "Testable statements" },
  { icon: FlaskConical, label: "Experiment", text: "Sandboxed reruns" },
  { icon: Microscope, label: "Evidence", text: "Measured results" },
  { icon: Scale, label: "Verdict", text: "Backend comparison" },
];

const LAB_STAGES = [
  "Paper enters",
  "Claim extraction",
  "Dataset loaded",
  "Model initialized",
  "Experiment runs",
  "Evidence collected",
  "Verdict generated",
];

function Section({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  const ref = useReveal<HTMLElement>();
  return (
    <section ref={ref} aria-label={title} className="reveal flex flex-col gap-4">
      <div>
        <p className="cl-meta font-medium uppercase tracking-[0.12em]">{eyebrow}</p>
        <h2 className="cl-h1 mt-1">{title}</h2>
      </div>
      {children}
    </section>
  );
}

/**
 * Home page: editorial marketing experience with the signature
 * laboratory visual. Spacious and story-driven by design — the audit
 * workspace deliberately looks nothing like this.
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
   * "Explore Demo" / "Try the demo run": re-upload the paper of a
   * finished demo run so the visitor watches a live pipeline. Falls
   * back to the demo gallery when no demo paper is available.
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

  const scrollToUpload = () => {
    document.getElementById("upload-heading")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="flex flex-col gap-14">
      {/* Hero: asymmetric editorial + laboratory */}
      <section aria-labelledby="hero-heading" className="grid items-center gap-8 pt-4 md:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] md:pt-8">
        <div className="flex max-w-xl flex-col gap-4">
          <p className="cl-meta font-medium uppercase tracking-[0.16em]">
            AI for reproducible research
          </p>
          <h1 id="hero-heading" className="cl-display text-[clamp(2.2rem,5vw,3.6rem)] leading-[1.05]">
            Audit research claims. Reproduce the evidence.
          </h1>
          <p className="cl-body max-w-md text-[var(--text-2)]">
            ClaimLens turns research papers into testable claims and compares
            published results with reproducible evidence.
          </p>
          <div className="mt-1 flex flex-wrap gap-2">
            <Button onClick={scrollToUpload}>Audit a Paper</Button>
            <Button variant="outline" onClick={() => void startDemo()} disabled={demoLoading}>
              {demoLoading ? "Starting demo…" : "Explore Demo"}
            </Button>
          </div>
          {demoError && (
            <p role="alert" className="text-sm text-[var(--bad)]">
              {demoError}
            </p>
          )}
        </div>
        <LabBeaker className="mx-auto w-full max-w-[520px]" />
      </section>

      {/* Upload: the main CTA */}
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

      {/* The problem */}
      <Section eyebrow="The problem" title="Research claims are published. But how often are they actually reproduced?">
        <p className="cl-body max-w-2xl text-[var(--text-2)]">
          Papers report state-of-the-art numbers, but rerunning their
          experiments takes days — and silent assumptions hide in every
          missing detail. ClaimLens makes reproduction routine: each claim
          gets its own experiment, its own evidence, and its own verdict.
        </p>
      </Section>

      {/* How it works: paper to verdict pipeline */}
      <Section eyebrow="How ClaimLens works" title="Paper → Claims → Experiment → Evidence → Verdict">
        <ol className="grid gap-2 sm:grid-cols-3 lg:grid-cols-5">
          {PIPELINE.map((step, i) => {
            const Icon = step.icon;
            return (
              <li key={step.label} className="cl-surface cl-lift relative p-4">
                <div className="flex items-center gap-2 text-[var(--accent)]">
                  <Icon size={18} aria-hidden="true" />
                  <span className="cl-mono text-xs">0{i + 1}</span>
                </div>
                <p className="mt-2 text-[0.9375rem] font-semibold">{step.label}</p>
                <p className="cl-meta mt-0.5">{step.text}</p>
                {i < PIPELINE.length - 1 && (
                  <span aria-hidden="true" className="absolute -right-2 top-1/2 hidden text-[var(--text-2)] lg:inline">
                    →
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </Section>

      {/* Interactive lab */}
      <Section eyebrow="The ClaimLens lab" title="Where published claims meet reproducible evidence.">
        <div className="grid items-center gap-6 md:grid-cols-2">
          <LabBeaker className="mx-auto w-full max-w-[560px]" />
          <ol className="flex flex-col gap-2" aria-label="Laboratory stages">
            {LAB_STAGES.map((stage, i) => (
              <li key={stage} className="lab-stage flex items-center gap-3">
                <span className="cl-mono text-xs text-[var(--text-2)]">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="text-sm font-medium">{stage}</span>
              </li>
            ))}
          </ol>
        </div>
        <p className="cl-meta flex items-center gap-4">
          <span className="inline-flex items-center gap-1.5">
            <Database size={14} aria-hidden="true" /> Dataset
          </span>
          <span className="inline-flex items-center gap-1.5">
            <GitBranch size={14} aria-hidden="true" /> Model
          </span>
          <span className="inline-flex items-center gap-1.5">
            <FlaskConical size={14} aria-hidden="true" /> Experiment
          </span>
        </p>
      </Section>

      {/* Audit example */}
      <Section eyebrow="Audit example" title="One claim, two numbers, zero ambiguity.">
        <div className="cl-surface grid gap-4 p-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
          <div>
            <p className="cl-mono text-xs text-[var(--text-2)]">CLAIM 02 · WMT 2014 EN–DE</p>
            <p className="mt-1 text-[0.9375rem]">
              The proposed architecture achieves state-of-the-art performance
              on the WMT 2014 dataset.
            </p>
            <dl className="mt-3 grid max-w-md grid-cols-3 gap-3">
              <div>
                <dt className="cl-meta uppercase tracking-[0.08em]">Reported</dt>
                <dd className="font-mono text-lg">28.4 BLEU</dd>
              </div>
              <div>
                <dt className="cl-meta uppercase tracking-[0.08em]">Reproduced</dt>
                <dd className="font-mono text-lg">27.9 BLEU</dd>
              </div>
              <div>
                <dt className="cl-meta uppercase tracking-[0.08em]">Difference</dt>
                <dd className="font-mono text-lg">−1.8%</dd>
              </div>
            </dl>
          </div>
          <VerdictBadge status="replicated" />
        </div>
      </Section>

      {/* Why it matters */}
      <Section eyebrow="Why it matters" title="Research, reproducibility, transparency.">
        <ul className="grid gap-2 md:grid-cols-3">
          {[
            { title: "Research", text: "Every claim traced to the exact section, table and page it came from." },
            { title: "Reproducibility", text: "Reduced-scale reruns with every assumption logged and justified." },
            { title: "Transparency", text: "Scaled runs can never refute a paper — limits are stated plainly." },
          ].map((item) => (
            <li key={item.title} className="cl-surface p-4">
              <p className="text-[0.9375rem] font-semibold">{item.title}</p>
              <p className="cl-meta mt-1">{item.text}</p>
            </li>
          ))}
        </ul>
      </Section>

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

      {/* Final CTA */}
      <section aria-labelledby="cta-heading" className="cl-surface flex flex-col items-start gap-3 p-6 md:p-8">
        <h2 id="cta-heading" className="cl-display text-2xl md:text-3xl">
          Make research claims auditable.
        </h2>
        <Button onClick={scrollToUpload}>Audit a Paper</Button>
      </section>
    </div>
  );
}
