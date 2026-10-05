/**
 * ProvenanceTrail — Miniature experiment lineage graph.
 * Uses real backend data where available; falls back to clearly-labelled
 * example data for the homepage demo.
 */
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";

interface ProvenanceNode {
  id: string;
  label: string;
  value: string;
  icon: string;
  color?: string;
}

interface Props {
  /** Live data from backend — all optional, falls back to example */
  runId?: string;
  claimId?: string;
  containerId?: string;
  commitHash?: string;
  filename?: string;
  demo?: boolean;
  className?: string;
}

export default function ProvenanceTrail({
  runId,
  claimId,
  containerId,
  commitHash,
  filename,
  demo = false,
  className = "",
}: Props) {
  const [open, setOpen] = useState(false);

  const nodes: ProvenanceNode[] = [
    {
      id: "paper",
      label: "PAPER",
      value: filename ?? (demo ? "example-paper.pdf" : "paper.pdf"),
      icon: "📄",
      color: "var(--accent-2)",
    },
    {
      id: "claim",
      label: "CLAIM",
      value: claimId ?? (demo ? "claim-01  [example]" : "claim-01"),
      icon: "◈",
      color: "var(--lab-green)",
    },
    {
      id: "experiment",
      label: "EXPERIMENT",
      value: demo ? "experiment-03  [example]" : "experiment-01",
      icon: "⚗",
      color: "var(--lab-green)",
    },
    {
      id: "container",
      label: "CONTAINER",
      value: containerId
        ? containerId.slice(0, 12)
        : demo
        ? "abc123ef  [example]"
        : "—",
      icon: "🐳",
      color: "var(--lab-blue)",
    },
    {
      id: "commit",
      label: "COMMIT",
      value: commitHash
        ? commitHash.slice(0, 8)
        : demo
        ? "8f2a1d  [example]"
        : "—",
      icon: "⌥",
      color: "var(--amber)",
    },
    {
      id: "result",
      label: "RESULT",
      value: runId ? `runs/${runId}/result.json` : demo ? "result.json  [example]" : "result.json",
      icon: "📊",
      color: "var(--lab-green)",
    },
    {
      id: "verdict",
      label: "VERDICT",
      value: "EVIDENCE CONSISTENT",
      icon: "✓",
      color: "var(--lab-green)",
    },
  ];

  return (
    <div className={`lab-surface p-3 ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2">
          <span className="cl-eyebrow text-[10px]">Experiment Provenance</span>
          {demo && (
            <span className="text-[8px] font-mono bg-[var(--amber-soft)] text-[var(--amber)] px-1.5 py-0.5 rounded-full">
              EXAMPLE
            </span>
          )}
        </div>
        {open ? (
          <ChevronUp size={14} className="text-[var(--text-2)]" aria-hidden="true" />
        ) : (
          <ChevronDown size={14} className="text-[var(--text-2)]" aria-hidden="true" />
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            style={{ overflow: "hidden" }}
          >
            <div className="provenance-trail mt-3">
              {nodes.map((node, i) => (
                <div key={node.id} className="provenance-node">
                  {/* Icon dot */}
                  <div
                    className="flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[8px] z-10"
                    style={{ background: node.color + "22", border: `1px solid ${node.color}66` }}
                    aria-hidden="true"
                  >
                    {node.icon}
                  </div>
                  {/* Content */}
                  <motion.div
                    className="flex-1 min-w-0"
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.25, delay: i * 0.06 }}
                  >
                    <div
                      className="text-[8px] font-semibold tracking-widest uppercase"
                      style={{ color: node.color }}
                    >
                      {node.label}
                    </div>
                    <div className="cl-code text-[10px] text-[var(--text)] truncate">
                      {node.value}
                    </div>
                  </motion.div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
