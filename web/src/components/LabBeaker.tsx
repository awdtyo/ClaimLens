import { cn } from "../lib/utils";

/**
 * Signature "digital laboratory" visual: a research paper releases
 * claim particles into a glass beaker where dataset/model/method/metric
 * layers mix, a measurement appears, and an evidence verdict settles.
 *
 * Pure SVG + CSS (8s loop, hover-reactive, theme-aware). No animation
 * libraries. Decorative motion only — the text summary below carries
 * the meaning for assistive technology and reduced-motion users.
 */
export default function LabBeaker({ className }: { className?: string }) {
  return (
    <figure className={cn("lab", className)} aria-label="Digital laboratory: a research paper releases claims into a mixing beaker that settles on verified evidence">
      <svg viewBox="0 0 360 320" role="img" aria-hidden="true" className="h-auto w-full">
        <defs>
          <clipPath id="lab-beaker-clip">
            <path d="M118 128 L124 268 Q125 278 135 278 L235 278 Q245 278 246 268 L252 128 Z" />
          </clipPath>
          <linearGradient id="lab-glass" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#ffffff" stopOpacity="0.10" />
            <stop offset="0.5" stopColor="#ffffff" stopOpacity="0.02" />
            <stop offset="1" stopColor="#ffffff" stopOpacity="0.09" />
          </linearGradient>
        </defs>

        {/* Research paper */}
        <g className="lab-paper">
          <rect x="22" y="26" width="62" height="82" rx="4" className="lab-doc" />
          <line x1="32" y1="44" x2="74" y2="44" className="lab-doc-line" />
          <line x1="32" y1="56" x2="74" y2="56" className="lab-doc-line" />
          <line x1="32" y1="68" x2="62" y2="68" className="lab-doc-line" />
          <line x1="32" y1="80" x2="68" y2="80" className="lab-doc-line" />
          <text x="22" y="122" className="lab-caption">RESEARCH PAPER</text>
        </g>

        {/* Claim particle stream: paper -> beaker */}
        <path
          d="M86 70 C 120 78, 128 96, 150 108"
          fill="none"
          className="lab-stream"
          strokeDasharray="3 7"
        />
        <circle r="3" className="lab-dot lab-dot-a" />
        <circle r="2.4" className="lab-dot lab-dot-b" />
        <circle r="2" className="lab-dot lab-dot-c" />
        <text x="96" y="66" className="lab-caption">CLAIMS</text>

        {/* Liquid layers inside beaker */}
        <g clipPath="url(#lab-beaker-clip)">
          <g className="lab-sway">
            <path
              d="M100 210 Q 130 200 160 210 T 220 210 T 280 210 L280 290 L100 290 Z"
              className="lab-liquid lab-layer-metric"
            />
            <path
              d="M100 232 Q 135 222 170 232 T 240 232 T 300 232 L300 290 L100 290 Z"
              className="lab-liquid lab-layer-model"
            />
            <path
              d="M100 252 Q 140 244 180 252 T 260 252 T 320 252 L320 290 L100 290 Z"
              className="lab-liquid lab-layer-dataset"
            />
          </g>
          {/* rising bubbles */}
          <circle cx="160" cy="250" r="2.5" className="lab-bubble lab-b1" />
          <circle cx="196" cy="262" r="1.8" className="lab-bubble lab-b2" />
          <circle cx="222" cy="246" r="2.2" className="lab-bubble lab-b3" />
          <circle cx="178" cy="258" r="1.5" className="lab-bubble lab-b4" />
          {/* slow swirl dots */}
          <g className="lab-swirl">
            <circle cx="185" cy="240" r="2" className="lab-swirl-dot" />
            <circle cx="205" cy="252" r="1.6" className="lab-swirl-dot" />
          </g>
          {/* measurement fill */}
          <line x1="246" y1="180" x2="246" y2="268" className="lab-measure-line" />
        </g>

        {/* Beaker glass */}
        <path
          d="M118 128 L124 268 Q125 278 135 278 L235 278 Q245 278 246 268 L252 128"
          fill="url(#lab-glass)"
          className="lab-glass"
        />
        <ellipse cx="185" cy="128" rx="67" ry="10" className="lab-glass-mouth" />
        <line x1="136" y1="150" x2="140" y2="248" className="lab-shine" />
        {/* measurement ticks */}
        <g className="lab-ticks">
          <line x1="252" y1="180" x2="260" y2="180" />
          <line x1="252" y1="206" x2="260" y2="206" />
          <line x1="252" y1="232" x2="260" y2="232" />
        </g>
        <text x="266" y="184" className="lab-caption lab-measure-text">87%</text>
        <text x="118" y="296" className="lab-caption">REPRODUCTION</text>

        {/* layer labels */}
        <g className="lab-layer-labels">
          <text x="262" y="222" className="lab-caption" data-layer="metric">METRIC</text>
          <text x="262" y="244" className="lab-caption" data-layer="model">MODEL</text>
          <text x="262" y="264" className="lab-caption" data-layer="dataset">DATASET</text>
        </g>

        {/* settling verdict */}
        <g className="lab-verdict">
          <rect x="112" y="36" width="146" height="26" rx="13" className="lab-verdict-pill" />
          <text x="185" y="53" textAnchor="middle" className="lab-verdict-text">
            ✓ EVIDENCE VERIFIED
          </text>
        </g>
        <text x="60" y="160" className="lab-caption">METHOD</text>
      </svg>

      {/* hover legend: highlights the matching liquid layer */}
      <figcaption className="lab-legend" aria-label="Beaker contents">
        {(
          [
            ["dataset", "Dataset · WMT 2014"],
            ["model", "Model · Transformer"],
            ["method", "Method · reproduction"],
            ["metric", "Metric · BLEU"],
          ] as const
        ).map(([layer, label]) => (
          <span key={layer} className="lab-legend-item" data-hl={layer} tabIndex={0}>
            {label}
          </span>
        ))}
      </figcaption>
      <p className="sr-only">
        A research paper releases claim particles into a beaker. Dataset, model
        and metric layers mix, the reproduction meter reaches 87 percent, and
        the result settles as verified evidence.
      </p>
    </figure>
  );
}
