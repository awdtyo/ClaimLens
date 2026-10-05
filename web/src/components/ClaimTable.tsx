import type { ClaimRow } from "../lib/claims";
import { shortReason } from "../lib/findings";
import { formatValue } from "../lib/format";
import VerdictBadge from "./VerdictBadge";
import { Chip } from "./ui";

interface ClaimTableProps {
  rows: ClaimRow[];
  selectedId: string | null;
  onSelect: (claimId: string) => void;
}

function difference(row: ClaimRow): string {
  const reported = row.claim.reported_value;
  const measured = row.measured;
  if (reported == null || measured == null || reported === 0) return "—";
  const d = measured - reported;
  const pct = (d / reported) * 100;
  return `${d > 0 ? "+" : ""}${d.toFixed(2)} (${pct > 0 ? "+" : ""}${pct.toFixed(1)}%)`;
}

/**
 * Research-oriented claim table (desktop) that transforms into compact
 * stacked claim items on mobile. Row selection drives the evidence
 * panel. Backend verdicts shown as-is.
 */
export default function ClaimTable({ rows, selectedId, onSelect }: ClaimTableProps) {
  return (
    <>
      {/* Desktop table */}
      <div className="cl-surface hidden overflow-x-auto !p-0 md:block">
        <table className="claim-table">
          <thead>
            <tr>
              <th style={{ width: 48 }}>#</th>
              <th>Claim</th>
              <th style={{ width: 105 }}>Reported</th>
              <th style={{ width: 105 }}>Reproduced</th>
              <th style={{ width: 90 }}>Δ</th>
              <th style={{ width: 130 }}>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const selected = row.claim.id === selectedId;
              const scaled = row.verdict?.scaled || (row.scaleFactor ?? 1) < 1;
              return (
                <tr
                  key={row.claim.id}
                  className="claim-row"
                  aria-selected={selected}
                  onClick={() => onSelect(row.claim.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect(row.claim.id);
                    }
                  }}
                  tabIndex={0}
                  aria-label={`Claim ${row.claim.id}: ${row.verdict?.status ?? "no verdict yet"}`}
                >
                  <td className="cl-mono whitespace-nowrap text-xs text-[var(--text-2)]">
                    {String(i + 1).padStart(2, "0")}
                  </td>
                  <td style={{ minWidth: 280 }}>
                    <p className="claim-cell-text line-clamp-2 max-w-prose text-[15px] leading-snug">
                      {row.claim.text}
                    </p>
                    <p className="cl-meta mt-0.5">
                      {row.claim.id} · {row.claim.source_ref}
                      {scaled && " · scaled"}
                    </p>
                    {row.verdict?.reason && (
                      <p className="cl-meta mt-0.5 italic" title={row.verdict.reason}>
                        {shortReason(row.verdict.reason, 70)}
                      </p>
                    )}
                  </td>
                  <td className="whitespace-nowrap font-mono text-[13px]">
                    {formatValue(row.claim.reported_value)}
                  </td>
                  <td className="whitespace-nowrap font-mono text-[13px]">
                    {formatValue(row.measured)}
                  </td>
                  <td className="whitespace-nowrap font-mono text-xs text-[var(--text-2)]">
                    {difference(row)}
                  </td>
                  <td>
                    {row.verdict ? (
                      <VerdictBadge status={row.verdict.status} />
                    ) : (
                      <Chip>pending</Chip>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile stacked items */}
      <ol aria-label="Claims" className="flex flex-col gap-3 md:hidden">
        {rows.map((row, i) => {
          const selected = row.claim.id === selectedId;
          return (
            <li key={row.claim.id} className="cl-surface cl-lift p-4">
              <button
                type="button"
                onClick={() => onSelect(row.claim.id)}
                aria-pressed={selected}
                aria-label={`Claim ${row.claim.id}: ${row.verdict?.status ?? "no verdict yet"}`}
                className="flex w-full flex-col gap-2 text-left"
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="cl-mono text-xs text-[var(--text-2)]">
                    CLAIM {String(i + 1).padStart(2, "0")}
                  </span>
                  {row.verdict ? (
                    <VerdictBadge status={row.verdict.status} />
                  ) : (
                    <Chip>pending</Chip>
                  )}
                </span>
                <span className="line-clamp-3 text-[15px] leading-snug">{row.claim.text}</span>
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                  <dt className="cl-meta">Reported</dt>
                  <dd className="font-mono text-[13px]">{formatValue(row.claim.reported_value)}</dd>
                  <dt className="cl-meta">Reproduced</dt>
                  <dd className="font-mono text-[13px]">{formatValue(row.measured)}</dd>
                  <dt className="cl-meta">Difference</dt>
                  <dd className="font-mono text-[13px]">{difference(row)}</dd>
                </dl>
                <span className="text-sm font-medium text-[var(--accent-2)]">View Evidence →</span>
              </button>
            </li>
          );
        })}
      </ol>
    </>
  );
}
