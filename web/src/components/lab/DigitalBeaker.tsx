import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

export type VerdictState = "idle" | "verified" | "partial" | "contradicted" | "inconclusive";

interface DigitalBeakerProps {
  verdict?: VerdictState;
  step?: number; // 0–10 animation step
  className?: string;
}

// Colour palettes per verdict
const PALETTE: Record<VerdictState, { liquid: string; particle: string; glow: string }> = {
  idle:         { liquid: "#3b657d", particle: "#7aa5c4", glow: "#3b657d33" },
  verified:     { liquid: "#15803d", particle: "#4ade80", glow: "#16a34a33" },
  partial:      { liquid: "#a16207", particle: "#fbbf24", glow: "#d9744133" },
  contradicted: { liquid: "#b3261e", particle: "#f87171", glow: "#dc262633" },
  inconclusive: { liquid: "#66706a", particle: "#9da8a1", glow: "#66706a22" },
};

const CODE_FRAGS = ["train()", "evaluate()", "forward()", "loss.backward()", "optimizer.step()", "metric()"];
const PARAMS = ["lr=3e-4", "batch=32", "seed=42", "epochs=10"];

export default function DigitalBeaker({ verdict = "idle", step = 10, className = "" }: DigitalBeakerProps) {
  const reduced = useReducedMotion();
  const pal = PALETTE[verdict];
  const animating = !reduced;
  const containerRef = useRef<HTMLDivElement>(null);

  const [particles, setParticles] = useState<Array<{ id: number; x: number; delay: number; frag: string }>>([]);
  const [paramParticles, setParamParticles] = useState<Array<{ id: number; x: number; delay: number; val: string }>>([]);
  const [bubbles, setBubbles] = useState<Array<{ id: number; x: number; delay: number; size: number }>>([]);

  useEffect(() => {
    if (!animating) return;
    setParticles(CODE_FRAGS.map((f, i) => ({ id: i, x: 20 + (i % 3) * 30, delay: i * 0.8, frag: f })));
    setParamParticles(PARAMS.map((p, i) => ({ id: i, x: 15 + i * 22, delay: i * 1.1 + 0.5, val: p })));
    setBubbles(Array.from({ length: 6 }, (_, i) => ({ id: i, x: 20 + i * 22, delay: i * 0.6, size: 4 + (i % 3) * 2 })));
  }, [animating]);

  const liquidHeight = Math.min(80, 20 + step * 6);

  return (
    <div ref={containerRef} className={`relative select-none ${className}`} aria-hidden="true">
      {/* Measurement marks */}
      <div className="absolute right-0 top-12 bottom-4 flex flex-col justify-between pr-1" style={{ pointerEvents: "none" }}>
        {[100, 75, 50, 25].map((v) => (
          <div key={v} className="flex items-center gap-1">
            <div className="h-px w-2 bg-[var(--text-2)] opacity-40" />
            <span className="cl-code text-[8px] text-[var(--text-2)] opacity-40">{v}</span>
          </div>
        ))}
      </div>

      <svg
        viewBox="0 0 160 220"
        width="160"
        height="220"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible"
      >
        {/* Defs: gradient, clip, glow filter */}
        <defs>
          <linearGradient id={`liquid-grad-${verdict}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={pal.liquid} stopOpacity="0.55" />
            <stop offset="100%" stopColor={pal.liquid} stopOpacity="0.82" />
          </linearGradient>
          <clipPath id="beaker-clip">
            <path d="M52 30 L52 130 Q52 195 80 200 Q108 205 108 130 L108 30 Z" />
          </clipPath>
          <filter id="beaker-glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="glass-sheen">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <radialGradient id="glass-highlight" cx="35%" cy="20%" r="55%">
            <stop offset="0%" stopColor="white" stopOpacity="0.25" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Flask body outline */}
        {/* Neck */}
        <path
          d="M62 10 L62 68 L38 145 Q28 175 80 182 Q132 189 122 145 L98 68 L98 10 Z"
          stroke={pal.liquid} strokeWidth="1.5" strokeOpacity="0.5"
          fill="url(#glass-highlight)"
        />
        {/* Rim */}
        <rect x="60" y="8" width="40" height="6" rx="3"
          stroke={pal.liquid} strokeWidth="1.2" strokeOpacity="0.6"
          fill="white" fillOpacity="0.08"
        />
        {/* Shoulder line */}
        <line x1="62" y1="68" x2="98" y2="68" stroke={pal.liquid} strokeWidth="0.8" strokeOpacity="0.3" strokeDasharray="2 3" />

        {/* Liquid fill */}
        <motion.path
          clipPath="url(#beaker-clip)"
          fill={`url(#liquid-grad-${verdict})`}
          initial={{ opacity: 0 }}
          animate={{
            opacity: step >= 3 ? 1 : 0,
            d: step >= 7
              ? `M28 ${182 - liquidHeight} Q54 ${182 - liquidHeight - 6} 80 ${182 - liquidHeight} Q106 ${182 - liquidHeight + 6} 132 ${182 - liquidHeight} L132 182 Q80 189 28 182 Z`
              : `M28 ${182 - liquidHeight} Q80 ${182 - liquidHeight + 2} 132 ${182 - liquidHeight} L132 182 Q80 189 28 182 Z`,
          }}
          transition={animating ? { duration: 1.8, ease: [0.22, 1, 0.36, 1] } : { duration: 0 }}
        />

        {/* Bubbles (step 7+) */}
        {animating && step >= 7 && bubbles.map((b) => (
          <motion.circle
            key={b.id}
            cx={40 + b.x}
            cy={175}
            r={b.size / 2}
            fill={pal.particle}
            fillOpacity="0.5"
            initial={{ cy: 175, opacity: 0.5 }}
            animate={{ cy: 120, opacity: 0 }}
            transition={{
              duration: 2 + b.delay * 0.3,
              delay: b.delay,
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        ))}

        {/* Neural network nodes (step 5+) */}
        {step >= 5 && (
          <g opacity="0.85">
            {/* Input layer */}
            {[0, 1, 2].map((i) => (
              <motion.circle key={`i${i}`} cx={50} cy={110 + i * 14} r={4}
                fill="none" stroke={pal.particle} strokeWidth="1.5"
                animate={animating ? { opacity: [0.4, 1, 0.4] } : {}}
                transition={{ duration: 1.4, delay: i * 0.2, repeat: Infinity }}
              />
            ))}
            {/* Hidden layer */}
            {[0, 1].map((i) => (
              <motion.circle key={`h${i}`} cx={80} cy={117 + i * 14} r={4}
                fill={pal.particle} fillOpacity="0.6" stroke={pal.particle} strokeWidth="1"
                animate={animating ? { r: [4, 5.5, 4], opacity: [0.6, 1, 0.6] } : {}}
                transition={{ duration: 1.8, delay: 0.3 + i * 0.3, repeat: Infinity }}
              />
            ))}
            {/* Output */}
            <motion.circle cx={110} cy={124} r={4.5}
              fill={pal.particle} fillOpacity="0.9" stroke={pal.liquid} strokeWidth="1.5"
              animate={animating ? { r: [4.5, 6, 4.5] } : {}}
              transition={{ duration: 1.6, delay: 0.6, repeat: Infinity }}
            />
            {/* Connections */}
            {[0, 1, 2].map((i) => [0, 1].map((j) => (
              <motion.line key={`e${i}${j}`}
                x1={54} y1={110 + i * 14} x2={76} y2={117 + j * 14}
                stroke={pal.particle} strokeWidth="0.8" strokeOpacity="0.35"
                animate={animating ? { strokeOpacity: [0.2, 0.6, 0.2] } : {}}
                transition={{ duration: 2, delay: (i + j) * 0.15, repeat: Infinity }}
              />
            )))}
            {[0, 1].map((j) => (
              <motion.line key={`eo${j}`}
                x1={84} y1={117 + j * 14} x2={106} y2={124}
                stroke={pal.particle} strokeWidth="0.8" strokeOpacity="0.35"
                animate={animating ? { strokeOpacity: [0.2, 0.7, 0.2] } : {}}
                transition={{ duration: 1.8, delay: 0.4 + j * 0.2, repeat: Infinity }}
              />
            ))}
          </g>
        )}

        {/* Code fragment particles entering (step 4+) */}
        {animating && step >= 4 && particles.slice(0, 3).map((p) => (
          <motion.text
            key={p.id}
            x={30 + p.x}
            y={60}
            fontSize="6"
            fill={pal.particle}
            opacity="0"
            fontFamily="monospace"
            animate={{
              y: [60, 80, 100],
              opacity: [0, 0.85, 0],
            }}
            transition={{
              duration: 2.5,
              delay: p.delay + 1,
              repeat: Infinity,
              ease: "easeIn",
            }}
          >
            {p.frag}
          </motion.text>
        ))}

        {/* Glass highlight overlay */}
        <path
          d="M68 12 Q65 50 64 70 L66 70 Q67 50 70 12 Z"
          fill="white" fillOpacity="0.15"
        />
        <path
          d="M42 90 Q38 120 36 155 Q55 165 38 158 Q36 120 40 90 Z"
          fill="white" fillOpacity="0.07"
        />

        {/* Measurement tick lines on flask */}
        {[40, 60, 80].map((y, i) => (
          <line key={i} x1={131} y1={y + 90} x2={136} y2={y + 90}
            stroke={pal.liquid} strokeWidth="1" strokeOpacity="0.4" />
        ))}

        {/* Step 10 — Verdict seal */}
        {step >= 10 && (
          <motion.g
            initial={{ scale: 0.7, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            style={{ transformOrigin: "80px 190px" }}
          >
            <circle cx="80" cy="192" r="14" fill={pal.liquid} fillOpacity="0.15"
              stroke={pal.liquid} strokeWidth="1.5" />
            <text x="80" y="197" textAnchor="middle" fontSize="9" fontWeight="bold"
              fill={pal.liquid} fontFamily="monospace">
              {verdict === "verified" ? "✓" : verdict === "contradicted" ? "✗" : verdict === "partial" ? "~" : "○"}
            </text>
          </motion.g>
        )}
      </svg>

      {/* Floating param particles */}
      {animating && step >= 6 && paramParticles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute cl-code text-[9px] pointer-events-none"
          style={{
            color: pal.particle,
            left: `${p.x}%`,
            top: "30%",
            opacity: 0,
          }}
          animate={{ y: [0, 20, 40], opacity: [0, 0.8, 0] }}
          transition={{ duration: 2.8, delay: p.delay, repeat: Infinity, ease: "easeIn" }}
        >
          {p.val}
        </motion.div>
      ))}
    </div>
  );
}
