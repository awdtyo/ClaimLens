/**
 * ReproducibilityCapsule — visual checklist of the 6 reproducibility ingredients.
 * Can be driven by real backend data (pass truthy booleans) or shown as demo.
 */
import { motion } from "framer-motion";
import { CheckCircle2, Circle } from "lucide-react";

interface Ingredient {
  label: string;
  check: boolean;
  detail?: string;
}

interface Props {
  data?: boolean;
  code?: boolean;
  environment?: boolean;
  parameters?: boolean;
  seed?: boolean;
  result?: boolean;
  /** Score 0–100, or null for demo */
  score?: number | null;
  demo?: boolean;
  className?: string;
}

export default function ReproducibilityCapsule({
  data = true,
  code = true,
  environment = true,
  parameters = true,
  seed = true,
  result = true,
  score = null,
  demo = false,
  className = "",
}: Props) {
  const ingredients: Ingredient[] = [
    { label: "Data",        check: data,        detail: "Dataset present" },
    { label: "Code",        check: code,        detail: "Code generated" },
    { label: "Environment", check: environment, detail: "Docker / Python" },
    { label: "Parameters",  check: parameters,  detail: "seed, lr, batch" },
    { label: "Seed",        check: seed,        detail: "Deterministic run" },
    { label: "Result",      check: result,      detail: "Measured output" },
  ];

  const passing = ingredients.filter((i) => i.check).length;
  const displayScore = score ?? Math.round((passing / ingredients.length) * 100);

  return (
    <div className={`repro-capsule ${className}`}>
      <div className="flex items-center justify-between px-3 py-2 bg-[var(--surface-2)] border-b border-[var(--border)]">
        <span className="cl-eyebrow text-[10px]">Reproducibility Capsule</span>
        <div className="flex items-center gap-2">
          {demo && (
            <span className="text-[8px] font-mono bg-[var(--amber-soft)] text-[var(--amber)] px-1.5 py-0.5 rounded-full">
              DEMO
            </span>
          )}
          <span className="cl-code text-[11px] font-semibold" style={{ color: "var(--lab-green)" }}>
            {displayScore} / 100
          </span>
        </div>
      </div>

      {/* Score bar */}
      <div className="px-3 pt-2 pb-1">
        <div className="lab-progress">
          <motion.div
            className="lab-progress-fill"
            initial={{ width: 0 }}
            animate={{ width: `${displayScore}%` }}
            transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[8px] text-[var(--text-2)]">Artifact completeness</span>
          <span className="cl-code text-[8px] text-[var(--lab-green)]">{passing}/{ingredients.length} present</span>
        </div>
      </div>

      {/* Ingredient rows */}
      {ingredients.map(({ label, check, detail }, i) => (
        <motion.div
          key={label}
          className="repro-capsule-row"
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: i * 0.07 }}
        >
          <div className="flex items-center gap-2">
            {check ? (
              <CheckCircle2 size={13} className="shrink-0" style={{ color: "var(--lab-green)" }} aria-hidden="true" />
            ) : (
              <Circle size={13} className="shrink-0" style={{ color: "var(--muted)" }} aria-hidden="true" />
            )}
            <span className="text-[12px] font-medium">{label}</span>
          </div>
          <span
            className="text-[10px] font-mono"
            style={{ color: check ? "var(--lab-green)" : "var(--muted)" }}
          >
            {check ? `✓  ${detail ?? ""}` : "—"}
          </span>
        </motion.div>
      ))}
    </div>
  );
}
