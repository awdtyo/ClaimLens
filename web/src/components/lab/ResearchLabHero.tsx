/**
 * ResearchLabHero — The signature homepage visual.
 *
 * Implements the full 10-step animation sequence:
 * paper → claims → dataset → code → model → params → run → measure → compare → verdict
 *
 * Layout:
 *   LEFT  — Digital lab canvas (beaker + panels)
 *   RIGHT — (used by parent HomePage)
 */
import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import DigitalBeaker, { type VerdictState } from "./DigitalBeaker";

const STEPS = [
  { id: 1,  label: "PAPER ENTERS",           detail: "Research paper" },
  { id: 2,  label: "CLAIMS EXTRACTED",        detail: "3 claims identified" },
  { id: 3,  label: "DATASET ENTERS",          detail: "Demo Dataset" },
  { id: 4,  label: "CODE ENTERS",             detail: "train() evaluate()" },
  { id: 5,  label: "MODEL ACTIVATES",         detail: "Transformer 6L" },
  { id: 6,  label: "PARAMETERS LOCK",         detail: "seed=42 lr=3e-4" },
  { id: 7,  label: "EXPERIMENT RUNS",         detail: "RUN 01 • RUNNING" },
  { id: 8,  label: "MEASUREMENTS APPEAR",     detail: "28.4 → 27.9" },
  { id: 9,  label: "COMPARISON",              detail: "Δ −1.8% ±5%" },
  { id: 10, label: "VERDICT",                 detail: "EVIDENCE CONSISTENT" },
] as const;

const VERDICT_SEQUENCE: VerdictState[] = [
  "idle", "idle", "idle", "idle", "idle",
  "idle", "idle", "idle", "partial",
  "verified",
];

export default function ResearchLabHero() {
  const reduced = useReducedMotion();
  const [step, setStep] = useState(reduced ? 10 : 0);
  const [running, setRunning] = useState(!reduced);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const verdict: VerdictState = VERDICT_SEQUENCE[Math.min(step, VERDICT_SEQUENCE.length - 1)];

  // Auto-advance steps
  useEffect(() => {
    if (!running || reduced) return;
    if (step >= 10) {
      // Pause then restart
      timerRef.current = setTimeout(() => { setStep(0); setRunning(true); }, 4000);
      return;
    }
    const delay = step === 0 ? 600 : step === 7 ? 1800 : step === 9 ? 1400 : 1100;
    timerRef.current = setTimeout(() => setStep((s) => s + 1), delay);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [step, running, reduced]);

  const currentStep = STEPS[Math.min(step - 1, STEPS.length - 1)];

  return (
    <div className="lab-grid lab-hero-wrapper p-4 md:p-6 flex flex-col gap-4" role="img" aria-label="Digital research laboratory visualization showing paper-to-verdict pipeline">

      {/* Top bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="cl-eyebrow">Digital Research Lab</span>
          <span className="lab-pill lab-verdict-verified text-[9px]">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true" />
            LIVE
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="cl-code text-[10px] text-[var(--text-2)]">
            {step < 10 ? `STEP ${String(step).padStart(2,"0")} / 10` : "COMPLETE"}
          </span>
          <button
            onClick={() => { setStep(0); setRunning(true); }}
            className="cl-code text-[10px] border border-[var(--border)] px-2 py-0.5 rounded hover:border-[var(--lab-green)] hover:text-[var(--lab-green)] transition-colors"
            aria-label="Restart laboratory animation"
            type="button"
          >
            ↺ Restart
          </button>
        </div>
      </div>

      {/* Main lab canvas */}
      <div className="flex gap-4 items-start min-h-[320px] relative">

        {/* LEFT: Paper + claims */}
        <div className="flex flex-col gap-3 flex-shrink-0 w-[120px]">
          {/* Paper card */}
          <motion.div
            className="lab-surface p-2 text-[10px] cursor-default"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: step >= 1 ? 1 : 0, x: step >= 1 ? 0 : -12 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="flex items-center gap-1 mb-1.5">
              <span className="text-[8px] font-bold tracking-widest text-[var(--text-2)]">RESEARCH PAPER</span>
            </div>
            {/* Simulated paper lines */}
            {[80, 70, 90, 60, 75, 85].map((w, i) => (
              <motion.div
                key={i}
                className="h-1 rounded-full mb-1"
                style={{
                  width: `${w}%`,
                  background: step >= 2 && i === 1
                    ? "var(--lab-green)"
                    : "var(--border)",
                  opacity: step >= 2 && i === 1 ? 1 : 0.6,
                }}
                animate={step >= 2 && i === 1 ? { opacity: [0.5, 1, 0.5] } : {}}
                transition={{ duration: 1.5, repeat: Infinity }}
              />
            ))}
            {step >= 2 && (
              <motion.div
                className="mt-1.5 text-[8px] font-mono text-[var(--lab-green)] font-semibold"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                → CLAIM 01
              </motion.div>
            )}
          </motion.div>

          {/* Claims list */}
          {step >= 2 && (
            <div className="flex flex-col gap-1">
              {["C-01", "C-02", "C-03"].map((c, i) => (
                <motion.div
                  key={c}
                  className="lab-surface text-[8px] px-2 py-1 font-mono text-[var(--lab-green)] flex items-center gap-1"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.35, delay: i * 0.15 }}
                >
                  <span className="inline-block w-1 h-1 rounded-full bg-[var(--lab-green)]" />
                  CLAIM {c.split("-")[1]}
                </motion.div>
              ))}
            </div>
          )}

          {/* Dataset box */}
          {step >= 3 && (
            <motion.div
              className="lab-surface p-2 text-[9px]"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <div className="cl-eyebrow mb-1 text-[8px]">DATASET</div>
              <div className="font-mono text-[var(--lab-blue)] text-[8px] leading-tight">
                <div>101101</div>
                <div>010011</div>
                <div>110010</div>
              </div>
              <div className="mt-1 text-[7px] text-[var(--text-2)]">Demo Dataset</div>
            </motion.div>
          )}
        </div>

        {/* CENTER: Beaker + arrow flow */}
        <div className="flex flex-col items-center gap-2 flex-1 relative">
          {/* Arrow from paper to beaker */}
          {step >= 3 && (
            <motion.div
              className="text-[var(--lab-green)] text-[10px] font-mono self-start pl-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
            >
              ↓ entering
            </motion.div>
          )}

          <DigitalBeaker verdict={verdict} step={step} />

          {/* Step indicator */}
          {currentStep && step > 0 && (
            <motion.div
              key={step}
              className="text-center"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="cl-code text-[8px] text-[var(--lab-green)] font-semibold tracking-wider">
                {currentStep.label}
              </div>
              <div className="text-[9px] text-[var(--text-2)] mt-0.5">{currentStep.detail}</div>
            </motion.div>
          )}

          {/* Measurement graph (step 8+) */}
          {step >= 8 && (
            <motion.div
              className="lab-surface w-full p-2 text-[9px]"
              initial={{ opacity: 0, scaleY: 0 }}
              animate={{ opacity: 1, scaleY: 1 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              style={{ transformOrigin: "bottom center" }}
            >
              <div className="cl-eyebrow text-[7px] mb-1">MEASUREMENT</div>
              <div className="flex gap-3 items-end">
                <div className="flex flex-col items-center gap-0.5">
                  <div className="text-[var(--text-2)] text-[8px]">Reported</div>
                  <motion.div
                    className="w-8 bg-[var(--accent-2)] rounded-t"
                    initial={{ height: 0 }}
                    animate={{ height: 28 }}
                    transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                  />
                  <span className="font-mono text-[8px]">28.4</span>
                </div>
                <div className="flex flex-col items-center gap-0.5">
                  <div className="text-[var(--text-2)] text-[8px]">Measured</div>
                  <motion.div
                    className="w-8 bg-[var(--lab-green)] rounded-t"
                    initial={{ height: 0 }}
                    animate={{ height: 26 }}
                    transition={{ duration: 0.8, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
                  />
                  <span className="font-mono text-[8px]">27.9</span>
                </div>
              </div>
              {step >= 9 && (
                <motion.div
                  className="mt-1 font-mono text-[8px] text-[var(--lab-amber)]"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.4 }}
                >
                  Δ −1.8% · tol ±5%
                </motion.div>
              )}
            </motion.div>
          )}
        </div>

        {/* RIGHT: Telemetry + environment */}
        <div className="flex flex-col gap-2 flex-shrink-0 w-[110px]">
          {/* Environment badges */}
          <motion.div
            className="lab-surface p-2"
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: step >= 1 ? 1 : 0, x: step >= 1 ? 0 : 12 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="cl-eyebrow text-[7px] mb-1.5">ENVIRONMENT</div>
            {[
              { label: "Python 3.11", active: step >= 1 },
              { label: "PyTorch",     active: step >= 5 },
              { label: "Docker",      active: step >= 7 },
              { label: "CUDA",        active: step >= 5 },
            ].map(({ label, active }) => (
              <div
                key={label}
                className="flex items-center gap-1 text-[8px] mb-0.5"
                style={{ color: active ? "var(--lab-green)" : "var(--text-2)", opacity: active ? 1 : 0.5 }}
              >
                <span>{active ? "✓" : "○"}</span>
                <span className="font-mono">{label}</span>
              </div>
            ))}
          </motion.div>

          {/* Seed lock */}
          {step >= 6 && (
            <motion.div
              className="lab-surface p-2"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
            >
              <div className="cl-eyebrow text-[7px] mb-1">RANDOMNESS</div>
              <div className="font-mono text-[10px] text-[var(--lab-green)] font-bold">SEED 42</div>
              <div className="text-[8px] text-[var(--lab-green)] mt-0.5">LOCKED ✓</div>
            </motion.div>
          )}

          {/* Config lock */}
          {step >= 6 && (
            <motion.div
              className="lab-surface p-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.2 }}
            >
              <div className="cl-eyebrow text-[7px] mb-1">CONFIG</div>
              {["lr=3e-4", "batch=32", "seed=42"].map((p) => (
                <div key={p} className="font-mono text-[8px] text-[var(--lab-blue)]">{p}</div>
              ))}
            </motion.div>
          )}

          {/* Run status */}
          {step >= 7 && (
            <motion.div
              className="lab-surface p-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
            >
              <div className="cl-eyebrow text-[7px] mb-1">STATUS</div>
              <div className="font-mono text-[9px] text-[var(--lab-green)]">
                {step < 10 ? "⟳ RUNNING..." : "✓ COMPLETE"}
              </div>
              {step >= 8 && (
                <div className="font-mono text-[8px] text-[var(--text-2)] mt-0.5">RUN 01</div>
              )}
            </motion.div>
          )}
        </div>
      </div>

      {/* Bottom step timeline */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1" role="list" aria-label="Experiment steps">
        {STEPS.map((s) => (
          <div
            key={s.id}
            role="listitem"
            className="flex flex-col items-center gap-0.5 min-w-[48px] cursor-pointer group"
            onClick={() => { setRunning(false); setStep(s.id); }}
            title={s.label}
          >
            <div
              className="w-6 h-1.5 rounded-full transition-all duration-300"
              style={{
                background: step >= s.id ? "var(--lab-green)" : "var(--border)",
                opacity: step === s.id ? 1 : step > s.id ? 0.8 : 0.35,
                transform: step === s.id ? "scaleY(1.5)" : undefined,
              }}
            />
            <span
              className="text-[7px] font-mono text-center leading-tight"
              style={{ color: step >= s.id ? "var(--lab-green)" : "var(--text-2)", opacity: step >= s.id ? 1 : 0.5 }}
            >
              {String(s.id).padStart(2, "0")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
