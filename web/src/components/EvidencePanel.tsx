import type { ClaimRow } from "../lib/claims";
import { formatValue } from "../lib/format";
import EvidenceTrail from "./EvidenceTrail";
import { Button } from "./ui";
import VerdictBadge from "./VerdictBadge";

/**
 * Evidence inspector panel: the selected claim's reported vs
 * reproduced comparison plus its evidence trail. Sticky, independently
 * scrollable column on desktop; bottom sheet content on mobile.
 */
export default function EvidencePanel({
  row,
  index,
  onViewFull,
}: {
  row: ClaimRow | null;
  index: number | null;
  onViewFull: () => void;
}) {
  if (!row) {
    return (
      <div className="evidence-panel">
        <p className="cl-meta font-medium uppercase tracking-[0.12em]">Evidence</p>
        <p className="cl-meta mt-2">Select a claim to inspect its evidence.</p>
      </div>
    );
  }
  const { claim, verdict, primaryEvidence } = row;
  const reported = claim.reported_value ?? null;
  const delta =
    reported !== null && row.measured !== null ? row.measured - reported : null;
  return (
    <div className="evidence-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="cl-meta font-medium uppercase tracking-[0.12em]">Evidence</p>
        {index !== null && (
          <p className="cl-mono text-xs text-[var(--text-2)]">Claim {String(index + 1).padStart(2, "0")}</p>
        )}
      </div>
      <div className="mt-1">
        {verdict ? <VerdictBadge status={verdict.status} /> : <p className="cl-meta">verdict pending</p>}
      </div>

      <hr className="evidence-divider" />

      <p className="cl-meta font-medium uppercase tracking-[0.1em]">The claim</p>
      <p className="mt-1 text-sm leading-relaxed">{claim.text}</p>

      <hr className="evidence-divider" />

      <dl className="flex flex-col gap-2">
        <div>
          <dt className="cl-meta font-medium uppercase tracking-[0.1em]">Reported</dt>
          <dd className="font-mono text-lg">{formatValue(reported)}</dd>
        </div>
        <div>
          <dt className="cl-meta font-medium uppercase tracking-[0.1em]">Reproduced</dt>
          <dd className="font-mono text-lg">{formatValue(row.measured)}</dd>
        </div>
        <div>
          <dt className="cl-meta font-medium uppercase tracking-[0.1em]">Difference</dt>
          <dd className="font-mono text-sm text-[var(--text-2)]">
            {delta !== null ? `${delta > 0 ? "+" : ""}${delta.toFixed(3)}` : "—"}
          </dd>
        </div>
      </dl>

      <hr className="evidence-divider" />

      <p className="cl-meta font-medium uppercase tracking-[0.1em]">Evidence trail</p>
      <div className="mt-2">
        <EvidenceTrail row={row} />
      </div>

      {primaryEvidence && (
        <>
          <hr className="evidence-divider" />
          <p className="cl-meta font-medium uppercase tracking-[0.1em]">Experiment</p>
          <p className="mt-1 text-sm">{primaryEvidence.method}</p>
          <p className="cl-meta mt-0.5">
            {primaryEvidence.id} · scale ×{primaryEvidence.scale_factor}
          </p>
        </>
      )}

      <div className="mt-3">
        <Button variant="outline" size="sm" onClick={onViewFull} className="w-full">
          View Full Evidence
        </Button>
      </div>
    </div>
  );
}
