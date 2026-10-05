/**
 * TerminalPanel — Simulated developer research terminal.
 * For homepage demo only. Animates the claimlens reproduce command output.
 * Does NOT fabricate real run data.
 */
import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

interface TerminalLine {
  text: string;
  type: "cmd" | "info" | "ok" | "warn" | "step";
  delay: number;
}

const DEMO_LINES: TerminalLine[] = [
  { text: "$ claimlens reproduce --claim 01 --demo", type: "cmd",  delay: 0 },
  { text: "> Loading dataset...",                     type: "info", delay: 600 },
  { text: "> Environment ready",                      type: "ok",   delay: 1100 },
  { text: "> Model initialized",                      type: "ok",   delay: 1600 },
  { text: "> Seed locked: 42",                        type: "ok",   delay: 2000 },
  { text: "> Running experiment...",                   type: "step", delay: 2500 },
  { text: "> Epoch 01/10  loss=0.412",                type: "info", delay: 3100 },
  { text: "> Epoch 05/10  loss=0.226",                type: "info", delay: 3600 },
  { text: "> Epoch 10/10  loss=0.184",                type: "info", delay: 4100 },
  { text: "> Evaluation complete",                    type: "ok",   delay: 4700 },
  { text: "> BLEU = 27.9",                            type: "ok",   delay: 5100 },
  { text: "> Comparing metrics...",                   type: "step", delay: 5500 },
  { text: "> Reported: 28.4  Measured: 27.9",        type: "info", delay: 5900 },
  { text: "> Difference: −1.8%  Tolerance: ±5%",     type: "info", delay: 6300 },
  { text: "✓ REPRODUCTION COMPLETE  [demo]",          type: "ok",   delay: 7000 },
];

const COLOR: Record<TerminalLine["type"], string> = {
  cmd:  "#a7f3d0",
  info: "#93c5fd",
  ok:   "#86efac",
  warn: "#fde68a",
  step: "#d4d4d8",
};

interface Props {
  className?: string;
  autoplay?: boolean;
}

export default function TerminalPanel({ className = "", autoplay = true }: Props) {
  const reduced = useReducedMotion();
  const [visibleCount, setVisibleCount] = useState(reduced ? DEMO_LINES.length : 0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!autoplay || reduced) return;
    const timers = DEMO_LINES.map((line, i) =>
      setTimeout(() => {
        setVisibleCount((c) => Math.max(c, i + 1));
      }, line.delay),
    );
    return () => timers.forEach(clearTimeout);
  }, [autoplay, reduced]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleCount]);

  const lines = DEMO_LINES.slice(0, visibleCount);
  const isComplete = visibleCount >= DEMO_LINES.length;

  return (
    <div className={`lab-terminal ${className}`} role="log" aria-label="Demo terminal output" aria-live="polite">
      {/* Title bar */}
      <div className="lab-terminal-header">
        <span className="lab-terminal-dot" style={{ background: "#ff5f57" }} aria-hidden="true" />
        <span className="lab-terminal-dot" style={{ background: "#febc2e" }} aria-hidden="true" />
        <span className="lab-terminal-dot" style={{ background: "#28c840" }} aria-hidden="true" />
        <span className="ml-2 text-[9px] tracking-wider opacity-50 text-[#a7f3d0]">
          claimlens — bash — demo
        </span>
        <span className="ml-auto text-[8px] opacity-40 text-[#a7f3d0]">DEMO</span>
      </div>

      {/* Output */}
      <div
        ref={scrollRef}
        className="p-3 min-h-[160px] max-h-[260px] overflow-y-auto scrollbar-thin"
        style={{ scrollbarColor: "rgba(167,243,208,0.15) transparent" }}
      >
        {lines.map((line, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
            style={{ color: COLOR[line.type] }}
            className="whitespace-pre-wrap"
          >
            {line.text}
          </motion.div>
        ))}

        {/* Blinking cursor */}
        {!isComplete && (
          <span
            className="anim-blink inline-block w-1.5 h-3 bg-[#a7f3d0] opacity-70 ml-0.5 align-middle"
            aria-hidden="true"
          />
        )}

        {isComplete && (
          <motion.div
            className="mt-2 text-[#86efac] font-bold text-[11px] tracking-wider"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
          >
            ─────────────────────────────────────
          </motion.div>
        )}
      </div>
    </div>
  );
}
