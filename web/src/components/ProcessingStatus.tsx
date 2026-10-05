import { getStageList, type RunDetail } from "../api/client";

/** Fixed agent checklist mapped onto real pipeline stages. */
const STEPS: { label: string; stages: string[] }[] = [
  { label: "Parsing paper", stages: ["ingest"] },
  { label: "Extracting claims", stages: ["claims"] },
  { label: "Preparing sandbox", stages: ["plan"] },
  { label: "Running experiments", stages: ["sandbox"] },
  { label: "Comparing results", stages: ["code_audit", "verify"] },
  { label: "Generating verdicts", stages: ["report"] },
];

function stepState(run: RunDetail, stages: string[]): "done" | "active" | "todo" {
  const states = stages.map((s) => run.stages?.[s]?.status ?? "pending");
  if (states.every((s) => s === "done")) return "done";
  if (states.some((s) => s === "running" || s === "failed")) return "active";
  // A later stage running implies earlier work finished.
  const order = getStageList(run);
  const latest = order.findIndex((s) => (run.stages?.[s]?.status ?? "pending") === "running");
  const mine = Math.min(...stages.map((s) => order.indexOf(s)).filter((i) => i >= 0));
  if (latest >= 0 && mine >= 0 && mine < latest) return "done";
  return "todo";
}

/**
 * Clean processing screen driven by real backend stage states.
 * Shows the ClaimLens agent checklist while a run is active, with a
 * small focused lab motif (not the homepage beaker).
 */
export default function ProcessingStatus({ run }: { run: RunDetail }) {
  return (
    <section aria-labelledby="audit-progress-heading" className="cl-surface flex flex-col gap-4 p-5">
      <div className="flex items-center gap-3">
        <svg viewBox="0 0 40 44" aria-hidden="true" className="lab-mini h-11 w-10 shrink-0">
          <path
            d="M15 4 h10 M17 4 v10 l-9 22 q-1 4 4 4 h16 q5 0 4 -4 l-9 -22 v-10"
            fill="none"
            stroke="var(--border)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="M11 30 h18 l2 6 q1 4 -4 4 h-14 q-5 0 -4 -4 Z" fill="var(--accent-soft)" />
          <circle cx="18" cy="34" r="1.6" className="lab-mini-bubble" />
          <circle cx="23" cy="36" r="1.2" className="lab-mini-bubble lab-mini-b2" />
          <circle cx="20" cy="37" r="1" className="lab-mini-bubble lab-mini-b3" />
        </svg>
        <div>
          <p className="cl-meta font-medium uppercase tracking-[0.12em]">ClaimLens lab</p>
          <h2 id="audit-progress-heading" className="cl-h1 mt-0.5">
            Auditing Your Paper
          </h2>
          <p className="cl-meta mt-1">
            ClaimLens is analyzing your paper and running reproduction experiments.
          </p>
        </div>
      </div>
      <div className="cl-progress" role="progressbar" aria-label="Audit progress">
        <span
          style={{
            width: `${Math.round(
              (STEPS.filter((s) => stepState(run, s.stages) === "done").length / STEPS.length) * 100,
            )}%`,
          }}
        />
      </div>
      <ol className="flex flex-col gap-1.5">
        {STEPS.map((step) => {
          const state = stepState(run, step.stages);
          return (
            <li key={step.label} className="flex items-center gap-2.5 text-sm">
              <span
                aria-hidden="true"
                className={
                  state === "done"
                    ? "inline-flex h-5 w-5 items-center justify-center rounded-full bg-[var(--ok-soft)] text-xs text-[var(--ok)]"
                    : state === "active"
                      ? "inline-flex h-5 w-5 items-center justify-center rounded-full bg-[var(--accent-soft)] text-xs text-[var(--accent)]"
                      : "inline-flex h-5 w-5 items-center justify-center rounded-full border border-[var(--border)] text-xs text-[var(--text-2)]"
                }
              >
                {state === "done" ? "✓" : state === "active" ? "●" : "○"}
              </span>
              <span className={state === "todo" ? "text-[var(--text-2)]" : undefined}>
                {step.label}
              </span>
              <span className="sr-only">{state === "done" ? "done" : state === "active" ? "in progress" : "pending"}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
