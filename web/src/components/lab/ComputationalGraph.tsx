/**
 * ComputationalGraph — ML experiment pipeline DAG.
 * Animates a signal travelling DATA → PREPROCESS → MODEL → EVALUATE → RESULT.
 * Hover over nodes for tooltip details.
 */
import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "../../lib/utils";

const NODES = [
  {
    id: "data",
    label: "DATA",
    detail: "DATASET\nDemo Dataset\nTrain: 1.2M samples",
    color: "var(--lab-blue)",
    softBg: "var(--accent-2-soft)",
  },
  {
    id: "preprocess",
    label: "PREPROCESS",
    detail: "PIPELINE\nTokenize\nNormalize\nSplit",
    color: "var(--accent-2)",
    softBg: "var(--accent-2-soft)",
  },
  {
    id: "model",
    label: "MODEL",
    detail: "MODEL\nTransformer\n6 layers · 8 heads",
    color: "var(--lab-green)",
    softBg: "var(--ok-soft)",
  },
  {
    id: "evaluate",
    label: "EVALUATE",
    detail: "METRIC\nBLEU\nHigher is better",
    color: "var(--amber)",
    softBg: "var(--amber-soft)",
  },
  {
    id: "result",
    label: "RESULT",
    detail: "RESULT\n27.9 BLEU\nDelta −1.8%",
    color: "var(--lab-green)",
    softBg: "var(--ok-soft)",
  },
] as const;

interface Props {
  activeNodeIndex?: number;
  className?: string;
}

export default function ComputationalGraph({ activeNodeIndex = -1, className = "" }: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const reduced = useReducedMotion();

  return (
    <div className={cn("flex flex-col items-center gap-0", className)} role="img" aria-label="Computational experiment pipeline graph">
      {NODES.map((node, i) => {
        const isActive = i <= activeNodeIndex;
        const isHovered = hoveredId === node.id;
        return (
          <div key={node.id} className="flex flex-col items-center">
            {/* Node */}
            <div
              className="comp-graph-node lab-tooltip-trigger"
              onMouseEnter={() => setHoveredId(node.id)}
              onMouseLeave={() => setHoveredId(null)}
              onFocus={() => setHoveredId(node.id)}
              onBlur={() => setHoveredId(null)}
              tabIndex={0}
              aria-label={`${node.label}: ${node.detail.replace(/\n/g, ", ")}`}
            >
              <motion.div
                className="comp-graph-node-box"
                animate={isActive && !reduced ? {
                  borderColor: [node.color + "66", node.color, node.color + "66"],
                  backgroundColor: [node.softBg, node.softBg, node.softBg],
                } : {}}
                style={{
                  borderColor: isActive ? node.color : undefined,
                  background: isActive ? node.softBg : undefined,
                  color: isActive ? node.color : "var(--text-2)",
                }}
                transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
              >
                {node.label}
              </motion.div>

              {/* Tooltip */}
              {isHovered && (
                <div
                  className="absolute bottom-full left-1/2 mb-2 z-20"
                  style={{ transform: "translateX(-50%)" }}
                >
                  <div className="lab-surface px-2.5 py-2 text-[10px] font-mono whitespace-pre text-[var(--text)] min-w-[120px] shadow-lg">
                    {node.detail}
                  </div>
                </div>
              )}
            </div>

            {/* Connector */}
            {i < NODES.length - 1 && (
              <div className="relative w-px" style={{ height: 18 }}>
                <div className="absolute inset-0 bg-[var(--border)]" />
                {isActive && !reduced && (
                  <motion.div
                    className="absolute left-0 right-0 rounded-full"
                    style={{ background: node.color, height: "35%" }}
                    animate={{ top: ["-35%", "100%"] }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.25, ease: "linear" }}
                  />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
