import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { artifactUrl, fetchRuns, uploadRun } from "../api/client";
import { useRuns } from "../hooks/useApi";
import { Button, Card, ErrorState } from "../components/ui";
import RunsList from "../components/RunsList";
import UploadDropzone from "../components/UploadDropzone";
import {
  ResearchLabHero,
  ExperimentTelemetry,
  ReproducibilityCapsule,
  TerminalPanel,
} from "../components/lab";

const HOW_IT_WORKS = [
  {
    n: "01",
    title: "Extract Claims",
    text: "ClaimLens parses the paper and identifies every quantitative, testable claim — each one mapped to a source sentence and metric.",
    icon: "📄",
  },
  {
    n: "02",
    title: "Plan Reproduction",
    text: "The AI planner designs a reduced-scale reproduction strategy: dataset, model architecture, hyperparameters, and environment.",
    icon: "⚗",
  },
  {
    n: "03",
    title: "Run in Sandbox",
    text: "Each experiment runs inside a locked Docker container with a fixed seed, fully isolated from external state.",
    icon: "🔬",
  },
  {
    n: "04",
    title: "Measure Evidence",
    text: "Reported values are compared to measured outputs within a scientific tolerance window. A verdict is assigned to each claim.",
    icon: "📊",
  },
] as const;

const VERDICTS = [
  {
    status: "VERIFIED",
    color: "var(--lab-green)",
    bg: "var(--ok-soft)",
    desc: "Measured evidence is consistent with the reported claim within tolerance.",
    icon: "✓",
  },
  {
    status: "PARTIAL",
    color: "var(--amber)",
    bg: "var(--amber-soft)",
    desc: "Partially consistent; reduced-scale result is directionally aligned.",
    icon: "~",
  },
  {
    status: "CONTRADICTED",
    color: "var(--bad)",
    bg: "var(--bad-soft)",
    desc: "Measured result differs significantly from the reported value.",
    icon: "✗",
  },
  {
    status: "INCONCLUSIVE",
    color: "var(--muted)",
    bg: "var(--muted-soft)",
    desc: "Insufficient evidence — claim cannot be tested at reduced scale.",
    icon: "○",
  },
] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: (i: number) => ({ opacity: 1, y: 0, transition: { duration: 0.5, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] as number[] } }),
};

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

  const startDemo = async () => {
    setDemoLoading(true);
    setDemoError(null);
    try {
      const demos = await fetchRuns(true);
      const demo = demos.find((d) => d.status === "done") ?? demos[0];
      if (!demo) { void navigate("/demos"); return; }
      const res = await fetch(artifactUrl(demo.run_id, "paper"));
      if (!res.ok) throw new Error(`Could not fetch the demo paper (HTTP ${res.status}).`);
      const blob = await res.blob();
      const file = new File([blob], demo.filename || "demo-paper.pdf", { type: "application/pdf" });
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
    <div className="flex flex-col gap-16 md:gap-20">

      {/* ═══════════════════════════════════════════════════
          SECTION 1 — HERO: editorial + lab
          ═══════════════════════════════════════════════════ */}
      <section
        aria-labelledby="hero-heading"
        className="grid gap-8 pt-4 md:grid-cols-2 md:items-start md:gap-10 md:pt-10"
      >
        {/* Left — editorial copy */}
        <div className="flex flex-col gap-5">
          <motion.p
            className="cl-eyebrow"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            AI for Reproducible Research
          </motion.p>

          <motion.h1
            id="hero-heading"
            className="cl-display"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
          >
            Audit Research Claims.
            <br />
            <em>Reproduce the Evidence.</em>
          </motion.h1>

          <motion.p
            className="cl-body text-[var(--text-2)] max-w-lg"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            ClaimLens turns research papers into testable claims and reconstructs
            the computational evidence behind them — dataset, code, model, and
            environment — in a locked sandbox.
          </motion.p>

          <motion.div
            className="flex flex-wrap gap-2 mt-1"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.3 }}
          >
            <Button
              onClick={() =>
                document.getElementById("upload-section")?.scrollIntoView({ behavior: "smooth" })
              }
            >
              Audit a Paper
            </Button>
            <Button
              variant="outline"
              onClick={() => void startDemo()}
              disabled={demoLoading}
            >
              {demoLoading ? "Starting demo…" : "Explore Demo"}
            </Button>
          </motion.div>

          {demoError && (
            <p role="alert" className="text-sm text-[var(--bad)]">{demoError}</p>
          )}

          {/* Signature claims preview */}
          <motion.div
            className="lab-surface p-3 mt-2 hidden md:block"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.45 }}
            aria-hidden="true"
          >
            <div className="cl-eyebrow text-[9px] mb-2">SAMPLE AUDIT RESULT</div>
            <div className="flex flex-col gap-1.5 font-mono text-[11px]">
              <div className="flex items-center gap-2">
                <span className="text-[var(--ok)]">✓</span>
                <span className="text-[var(--text-2)]">claim c1</span>
                <span className="ml-auto text-[var(--ok)]">replicated (91.1 vs 91.2)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[var(--warn)]">~</span>
                <span className="text-[var(--text-2)]">claim c2</span>
                <span className="ml-auto text-[var(--warn)]">partial (scaled ×0.1)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[var(--muted)]">○</span>
                <span className="text-[var(--text-2)]">claim c4</span>
                <span className="ml-auto text-[var(--muted)]">inconclusive (no data)</span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Right — the digital research lab */}
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
        >
          <ResearchLabHero />
        </motion.div>
      </section>

      {/* ═══════════════════════════════════════════════════
          SECTION 2 — UPLOAD
          ═══════════════════════════════════════════════════ */}
      <section
        id="upload-section"
        aria-labelledby="upload-heading"
        className="scroll-mt-20 flex flex-col gap-4"
      >
        <div className="lab-section-label">Start an audit</div>
        <div className="grid gap-6 md:grid-cols-[1fr_auto]">
          <div>
            <h2 id="upload-heading" className="cl-h1">Upload a Research Paper</h2>
            <p className="cl-meta mt-1">
              Drag &amp; drop your PDF or browse. PDF · up to 30 MB.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Link to="/demos" className="cl-btn cl-btn-outline cl-btn-sm">
              Browse demo audits
            </Link>
          </div>
        </div>
        <Card>
          <UploadDropzone
            uploading={uploadMutation.isPending}
            error={uploadError}
            onFile={(file) => uploadMutation.mutate(file)}
          />
          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-[var(--border)] pt-4">
            <span className="cl-meta">No paper?</span>
            <Button
              variant="outline"
              disabled={demoLoading || uploadMutation.isPending}
              onClick={() => void startDemo()}
            >
              {demoLoading ? "Starting demo…" : "Try the demo run"}
            </Button>
          </div>
        </Card>
      </section>

      {/* ═══════════════════════════════════════════════════
          SECTION 3 — HOW IT WORKS (scroll story)
          ═══════════════════════════════════════════════════ */}
      <section
        id="how-it-works"
        aria-labelledby="how-heading"
        className="scroll-mt-20 flex flex-col gap-6"
      >
        <div className="lab-section-label">The pipeline</div>
        <div>
          <h2 id="how-heading" className="cl-display" style={{ fontSize: "clamp(1.6rem, 3vw, 2.2rem)" }}>
            From paper to verdict
          </h2>
          <p className="cl-body text-[var(--text-2)] mt-2 max-w-xl">
            A single research paper triggers a fully automated computational audit.
          </p>
        </div>

        {/* Visual pipeline: paper → claims → lab → evidence → verdict */}
        <div className="relative">
          {/* Connecting line (desktop) */}
          <div
            className="hidden md:block absolute top-[52px] left-[calc(12.5%+20px)] right-[calc(12.5%+20px)] h-px"
            style={{ background: "var(--border)" }}
            aria-hidden="true"
          />

          <ol className="grid gap-4 md:grid-cols-4 relative">
            {HOW_IT_WORKS.map((step, i) => (
              <motion.li
                key={step.n}
                className="cl-surface cl-lift flex flex-col gap-2 p-5 relative"
                custom={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, amount: 0.3 }}
                variants={fadeUp}
              >
                <span
                  aria-hidden="true"
                  className="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface-2)] text-lg"
                >
                  {step.icon}
                </span>
                <span className="cl-eyebrow text-[9px] mt-1">{step.n}</span>
                <p className="text-[0.9375rem] font-semibold">{step.title}</p>
                <p className="cl-meta">{step.text}</p>
              </motion.li>
            ))}
          </ol>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════
          SECTION 4 — LAB DETAIL: telemetry + terminal
          ═══════════════════════════════════════════════════ */}
      <section aria-labelledby="lab-heading" className="scroll-mt-20 flex flex-col gap-6">
        <div className="lab-section-label">Inside the lab</div>
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h2 id="lab-heading" className="cl-display" style={{ fontSize: "clamp(1.5rem, 2.5vw, 2rem)" }}>
              Every experiment is measured.
            </h2>
            <p className="cl-body text-[var(--text-2)] mt-2">
              ClaimLens runs real code — not a text comparison. It tracks
              dataset, model, parameters, seed, and environment for every claim it tests.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <ExperimentTelemetry />
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <TerminalPanel autoplay />
          <ReproducibilityCapsule demo />
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════
          SECTION 5 — VERDICTS
          ═══════════════════════════════════════════════════ */}
      <section aria-labelledby="verdicts-heading" className="scroll-mt-20 flex flex-col gap-6">
        <div className="lab-section-label">Verdict system</div>
        <h2 id="verdicts-heading" className="cl-h1">
          What each verdict means
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {VERDICTS.map((v, i) => (
            <motion.div
              key={v.status}
              className="cl-surface cl-lift flex flex-col gap-2 p-4"
              custom={i}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.3 }}
              variants={fadeUp}
            >
              <div
                className="flex h-9 w-9 items-center justify-center rounded-full text-lg font-bold"
                style={{ background: v.bg, color: v.color }}
                aria-hidden="true"
              >
                {v.icon}
              </div>
              <p
                className="font-semibold tracking-wide text-sm"
                style={{ color: v.color }}
              >
                {v.status}
              </p>
              <p className="cl-meta">{v.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════
          SECTION 6 — PAST AUDITS
          ═══════════════════════════════════════════════════ */}
      <section
        id="audits"
        aria-labelledby="runs-heading"
        className="scroll-mt-20 flex flex-col gap-4"
      >
        <div className="lab-section-label">Audit history</div>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="runs-heading" className="cl-h1">Past audits</h2>
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

      {/* ═══════════════════════════════════════════════════
          INTEGRITY NOTE
          ═══════════════════════════════════════════════════ */}
      <aside
        aria-label="Research integrity note"
        className="lab-surface p-4 flex flex-col gap-1.5"
      >
        <p className="text-sm font-semibold">Research Integrity</p>
        <p className="cl-meta max-w-3xl">
          ClaimLens performs reduced-scale reproduction experiments. A failed
          reproduction does not automatically prove that the original paper is
          incorrect. Verdicts are computed by the backend; the frontend never
          decides whether results match.
        </p>
      </aside>
    </div>
  );
}
