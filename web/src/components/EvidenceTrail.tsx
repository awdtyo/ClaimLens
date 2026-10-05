import type { ClaimRow } from "../lib/claims";

/**
 * Evidence trail: Paper → Claim → Dataset → Method → Experiment →
 * Result → Verdict. Built only from real backend data; steps without
 * data are marked "not recorded".
 */
export default function EvidenceTrail({ row }: { row: ClaimRow }) {
  const { claim, verdict, primaryEvidence } = row;
  const dataset = (claim as unknown as { dataset?: string | null }).dataset ?? null;
  const steps: { label: string; value: string }[] = [
    { label: "Paper", value: claim.source_ref || "not recorded" },
    { label: "Claim", value: claim.id },
    { label: "Dataset", value: dataset || "not recorded" },
    { label: "Method", value: primaryEvidence?.method || "not recorded" },
    {
      label: "Experiment",
      value:
        primaryEvidence != null
          ? `${primaryEvidence.id} · scale ×${primaryEvidence.scale_factor}`
          : "not recorded",
    },
    {
      label: "Result",
      value:
        row.measured !== null && row.measured !== undefined
          ? String(row.measured)
          : "not recorded",
    },
    { label: "Verdict", value: verdict?.status ?? "pending" },
  ];
  return (
    <ol aria-label="Evidence trail" className="flex flex-col">
      {steps.map((step, i) => (
        <li key={step.label} className="relative flex gap-3 pb-3 last:pb-0">
          {i < steps.length - 1 && (
            <span aria-hidden="true" className="absolute bottom-0 left-[5px] top-5 w-px bg-[var(--border)]" />
          )}
          <span
            aria-hidden="true"
            className="mt-1.5 h-[7px] w-[7px] shrink-0 rounded-full border border-[var(--accent)] bg-[var(--surface)]"
          />
          <div className="min-w-0">
            <p className="cl-meta font-medium uppercase tracking-[0.08em]">{step.label}</p>
            <p className="truncate text-sm">{step.value}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
