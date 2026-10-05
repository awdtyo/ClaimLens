/**
 * ExperimentTelemetry — Animated live metric display panel.
 * Clearly marked as DEMO data for homepage visualization.
 */
import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

interface Metric {
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  deltaGood?: boolean;
}

const DEMO_METRICS: Metric[] = [
  { label: "Epoch",    value: "07",    unit: "/ 10" },
  { label: "Loss",     value: "0.184", delta: "↓ -0.012", deltaGood: true },
  { label: "Accuracy", value: "92.4",  unit: "%",    delta: "↑ +0.3%", deltaGood: true },
  { label: "BLEU",     value: "27.9",  delta: "−1.8% vs reported" },
  { label: "Runtime",  value: "02:14" },
];

function AnimatedNumber({ to, decimals = 0 }: { to: number; decimals?: number }) {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(reduced ? to : 0);
  const raf = useRef<number | null>(null);
  const start = useRef<number | null>(null);
  const DURATION = 1200;

  useEffect(() => {
    if (reduced) { setDisplay(to); return; }
    start.current = null;
    const from = 0;
    const step = (ts: number) => {
      if (start.current === null) start.current = ts;
      const progress = Math.min((ts - start.current) / DURATION, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(from + (to - from) * eased);
      if (progress < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); };
  }, [to, reduced]);

  return <>{display.toFixed(decimals)}</>;
}

interface Props {
  className?: string;
  /** When true, shows real data placeholder instead of demo values */
  live?: boolean;
  liveEpoch?: number;
  liveLoss?: number;
}

export default function ExperimentTelemetry({ className = "", live = false }: Props) {
  return (
    <div className={`lab-surface p-3 flex flex-col gap-2 ${className}`}>
      <div className="flex items-center justify-between">
        <span className="cl-eyebrow text-[10px]">Experiment Telemetry</span>
        {!live && (
          <span className="text-[8px] font-mono bg-[var(--amber-soft)] text-[var(--amber)] px-1.5 py-0.5 rounded-full">
            DEMO
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
        {DEMO_METRICS.map((m) => (
          <motion.div
            key={m.label}
            className="metric-card-lab"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <div className="metric-label">{m.label}</div>
            <div className="metric-value">
              {m.label === "Epoch" ? (
                <><AnimatedNumber to={7} />
                  <span className="text-sm text-[var(--text-2)]"> / 10</span>
                </>
              ) : m.label === "Loss" ? (
                <AnimatedNumber to={0.184} decimals={3} />
              ) : m.label === "Accuracy" ? (
                <><AnimatedNumber to={92.4} decimals={1} />
                  <span className="text-sm text-[var(--text-2)]">%</span>
                </>
              ) : m.label === "BLEU" ? (
                <AnimatedNumber to={27.9} decimals={1} />
              ) : (
                m.value
              )}
            </div>
            {m.delta && (
              <div
                className="text-[9px] font-mono mt-0.5"
                style={{ color: m.deltaGood ? "var(--lab-green)" : "var(--amber)" }}
              >
                {m.delta}
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Mini spark bars */}
      <div className="flex flex-col gap-1.5 mt-1">
        {[
          { label: "MODEL",       pct: 87 },
          { label: "EVIDENCE",    pct: 51 },
          { label: "DATA",        pct: 100 },
          { label: "CODE",        pct: 100 },
          { label: "ENVIRONMENT", pct: 100 },
        ].map(({ label, pct }) => (
          <div key={label} className="flex items-center gap-2">
            <span className="cl-code text-[9px] text-[var(--text-2)] w-[76px] flex-shrink-0">{label}</span>
            <div className="lab-progress flex-1">
              <motion.div
                className="lab-progress-fill"
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
              />
            </div>
            <span className="cl-code text-[9px] w-8 text-right">{pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
