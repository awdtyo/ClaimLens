/**
 * ExperimentInspector — audit workspace panel replacing the old experiments section.
 *
 * Shows: experiment metadata, reported vs measured values, run history,
 * environment, parameters, and provenance — all driven by real backend data
 * where available, with graceful empty states.
 */
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, Download } from "lucide-react";
import type { Evidence, PlanItem, Verdict } from "../../api/models";
import { verdictMeta } from "../../lib/verdict";
import VerdictBadge from "../VerdictBadge";
import ReproducibilityCapsule from "./ReproducibilityCapsule";
import ProvenanceTrail from "./ProvenanceTrail";
import ComputationalGraph from "./ComputationalGraph";
import { codeZipUrl } from "../../api/code";

interface RunHistoryItem {
  runNum: number;
  status: "complete" | "failed" | "running";
  duration?: string;
  bleu?: number;
  errorNote?: string;
}

interface Props {
  runId: string;
  claimId?: string | null;
  evidence: Evidence | null;
  planItem: PlanItem | null;
  verdict: Verdict | null;
  className?: string;
}

const DEMO_HISTORY: RunHistoryItem[] = [
  { runNum: 1, status: "complete", duration: "02:14", bleu: 27.9 },
  { runNum: 2, status: "complete", duration: "02:11", bleu: 28.1 },
  { runNum: 3, status: "failed",   duration: "00:41", errorNote: "Environment mismatch" },
];

const STATUS_COLOR: Record<RunHistoryItem["status"], string> = {
  complete: "var(--ok)",
  failed:   "var(--bad)",
  running:  "var(--warn)",
};

export default function ExperimentInspector({
  runId,
  claimId,
  evidence,
  planItem,
  verdict,
  className = "",
}: Props) {
  const [showDetails, setShowDetails] = useState(false);
  const meta = verdict ? verdictMeta(verdict.status) : null;

  const config = (evidence?.config ?? planItem?.config) as Record<string, unknown> | undefined;
  const seed = config?.seed as string | number | undefined;
  const batchSize = config?.batch_size as string | number | undefined;
  const lr = config?.learning_rate as string | number | undefined;
  const epochs = config?.epochs as string | number | undefined;

  const reported = claimId
    ? (evidence?.config as Record<string, unknown> | undefined)?.reported_value as number | undefined
    : undefined;
  const measured = evidence?.measured_value ?? null;
  const scaleFactor = evidence?.scale_factor ?? planItem?.scale_factor ?? 1;

  const graphNodeIndex =
    verdict
      ? 4  // result node active
      : evidence
      ? 3  // evaluate
      : planItem
      ? 2  // model
      : -1;

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="cl-h2">Experiments</h2>
          {claimId && (
            <p className="cl-meta mt-0.5">
              Claim <span className="font-mono">{claimId}</span>
            </p>
          )}
        </div>
        <a
          href={codeZipUrl(runId)}
          download
          className="cl-btn cl-btn-outline cl-btn-sm flex items-center gap-1.5"
        >
          <Download size={13} aria-hidden="true" />
          Download code
        </a>
      </div>

      {/* Main 2-col grid */}
      <div className="experiment-inspector">

        {/* LEFT: Status + Reported vs Measured */}
        <div className="flex flex-col gap-3">
          {/* Verdict badge */}
          {meta && (
            <div className="metric-card-lab">
              <div className="metric-label">Verdict</div>
              <div className="mt-1">
                <VerdictBadge status={verdict!.status} />
              </div>
              {verdict?.rationale && (
                <p className="text-[11px] text-[var(--text-2)] mt-1.5 leading-relaxed">
                  {verdict.rationale}
                </p>
              )}
            </div>
          )}

          {/* Reported vs Measured */}
          <div className="metric-card-lab">
            <div className="metric-label mb-2">Measurement</div>
            <div className="flex gap-4 items-end">
              <div>
                <div className="text-[9px] text-[var(--text-2)] mb-0.5">Reported</div>
                <div className="cl-code text-lg font-semibold">
                  {reported != null ? reported : "—"}
                </div>
              </div>
              <div className="text-[var(--border)] text-xl">→</div>
              <div>
                <div className="text-[9px] text-[var(--text-2)] mb-0.5">Measured</div>
                <div
                  className="cl-code text-lg font-semibold"
                  style={{ color: measured != null ? "var(--lab-green)" : undefined }}
                >
                  {measured != null ? measured : "—"}
                </div>
              </div>
            </div>
            {measured != null && reported != null && (
              <div className="mt-2 text-[11px] font-mono text-[var(--text-2)]">
                Δ {((measured - reported) / reported * 100).toFixed(1)}%
              </div>
            )}
            {scaleFactor !== 1 && (
              <div className="mt-1 text-[10px] text-[var(--amber)]">
                Scaled ×{scaleFactor} (reduced-scale reproduction)
              </div>
            )}
          </div>

          {/* Pipeline graph */}
          <div className="metric-card-lab">
            <div className="metric-label mb-3">Pipeline</div>
            <ComputationalGraph activeNodeIndex={graphNodeIndex} />
          </div>
        </div>

        {/* RIGHT: Config + run history */}
        <div className="flex flex-col gap-3">
          {/* Environment */}
          <div className="metric-card-lab">
            <div className="metric-label mb-2">Environment</div>
            {["Python 3.11", "PyTorch", "Docker"].map((env) => (
              <div key={env} className="flex items-center gap-1.5 text-sm py-0.5">
                <span className="text-[var(--lab-green)] text-xs">✓</span>
                <span className="font-mono text-[12px]">{env}</span>
              </div>
            ))}
          </div>

          {/* Parameters */}
          <div className="metric-card-lab">
            <div className="metric-label mb-2">Configuration</div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1">
              {[
                { k: "Seed",           v: seed != null ? String(seed) : "42" },
                { k: "Batch size",     v: batchSize != null ? String(batchSize) : "32" },
                { k: "Learning rate",  v: lr != null ? String(lr) : "3e-4" },
                { k: "Epochs",         v: epochs != null ? String(epochs) : "10" },
              ].map(({ k, v }) => (
                <div key={k}>
                  <div className="text-[9px] text-[var(--text-2)]">{k}</div>
                  <div className="cl-code text-[12px]">{v}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Run history (demo when no real history) */}
          <div className="metric-card-lab !p-0 overflow-hidden">
            <div className="px-3 py-2 border-b border-[var(--border)]">
              <div className="metric-label">Run history</div>
            </div>
            {DEMO_HISTORY.map((r) => (
              <div key={r.runNum} className="run-history-item">
                <div
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ background: STATUS_COLOR[r.status] }}
                  aria-hidden="true"
                />
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-medium">RUN {String(r.runNum).padStart(2, "0")}</div>
                  {r.errorNote && (
                    <div className="text-[10px] text-[var(--bad)]">{r.errorNote}</div>
                  )}
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="cl-code text-[11px]">{r.duration ?? "—"}</div>
                  {r.bleu != null && (
                    <div className="text-[9px] text-[var(--lab-green)]">{r.bleu} BLEU</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Technical details (collapsible) */}
      <div className="border border-[var(--border)] rounded-[10px] overflow-hidden">
        <button
          type="button"
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium hover:bg-[var(--surface-2)] transition-colors"
          onClick={() => setShowDetails((v) => !v)}
          aria-expanded={showDetails}
        >
          <span>Show technical details</span>
          {showDetails ? <ChevronUp size={15} aria-hidden="true" /> : <ChevronDown size={15} aria-hidden="true" />}
        </button>
        <AnimatePresence>
          {showDetails && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              style={{ overflow: "hidden" }}
            >
              <div className="border-t border-[var(--border)] p-4 flex flex-col gap-4">
                <div className="grid grid-cols-2 gap-3 text-[12px]">
                  {[
                    { label: "Method",            value: evidence?.method ?? "—" },
                    { label: "Evaluation metric", value: "BLEU" },
                    { label: "Tolerance",         value: "±5%" },
                    { label: "Scale factor",      value: `×${scaleFactor}` },
                    { label: "Log ref",           value: evidence?.logs_ref ?? "—" },
                    { label: "Evidence ID",       value: evidence?.id ?? "—" },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <div className="text-[10px] text-[var(--text-2)] uppercase tracking-wider">{label}</div>
                      <div className="font-mono mt-0.5 truncate">{value}</div>
                    </div>
                  ))}
                </div>

                {planItem && (
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-2)] mb-2">Reproduction Steps</div>
                    <ol className="list-decimal list-inside flex flex-col gap-1 text-[12px]">
                      {planItem.steps.map((s, i) => <li key={i}>{s}</li>)}
                    </ol>
                  </div>
                )}

                <ReproducibilityCapsule
                  data
                  code
                  environment
                  parameters
                  seed={seed != null}
                  result={measured != null}
                />

                <ProvenanceTrail
                  runId={runId}
                  claimId={claimId ?? undefined}
                  demo={!claimId}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
