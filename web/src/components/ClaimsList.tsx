import { useMemo, useState } from "react";
import type { ClaimRow, ClaimFilter, ClaimSortKey } from "../lib/claims";
import { filterClaimRows, sortClaimRows } from "../lib/claims";
import { VERDICT_ORDER } from "../lib/verdict";
import { formatValue } from "../lib/format";
import { Chip, EmptyState } from "./ui";
import VerdictBadge from "./VerdictBadge";

interface ClaimsListProps {
  rows: ClaimRow[];
  selectedId: string | null;
  onSelect: (claimId: string) => void;
}

const SORT_OPTIONS: { value: ClaimSortKey; label: string }[] = [
  { value: "id", label: "Claim ID" },
  { value: "verdict", label: "Verdict" },
  { value: "reported", label: "Reported value" },
  { value: "measured", label: "Measured value" },
];

/**
 * Filterable, sortable claim list. Each row shows the claim text, the
 * backend verdict badge, reported and measured values, and a
 * scale-factor chip when the run was scaled down.
 */
export default function ClaimsList({ rows, selectedId, onSelect }: ClaimsListProps) {
  const [filter, setFilter] = useState<ClaimFilter>({
    bucket: "all",
    query: "",
    scaledOnly: false,
  });
  const [sortKey, setSortKey] = useState<ClaimSortKey>("id");
  const [sortDir, setSortDir] = useState<1 | -1>(1);

  const visible = useMemo(
    () => sortClaimRows(filterClaimRows(rows, filter), sortKey, sortDir),
    [rows, filter, sortKey, sortDir],
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2" role="search" aria-label="Filter claims">
        <label className="sr-only" htmlFor="claim-filter-verdict">
          Filter by verdict
        </label>
        <select
          id="claim-filter-verdict"
          value={filter.bucket}
          onChange={(e) =>
            setFilter((f) => ({ ...f, bucket: e.target.value as ClaimFilter["bucket"] }))
          }
          className="h-9 rounded-md border border-gray-300 bg-white px-2 text-sm dark:border-gray-700 dark:bg-gray-900"
        >
          <option value="all">All verdicts</option>
          {VERDICT_ORDER.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
        <label className="sr-only" htmlFor="claim-filter-query">
          Search claims
        </label>
        <input
          id="claim-filter-query"
          type="search"
          placeholder="Search claim text…"
          value={filter.query}
          onChange={(e) => setFilter((f) => ({ ...f, query: e.target.value }))}
          className="h-9 min-w-40 flex-1 rounded-md border border-gray-300 bg-white px-2 text-sm dark:border-gray-700 dark:bg-gray-900"
        />
        <label className="inline-flex cursor-pointer items-center gap-1.5 text-sm">
          <input
            type="checkbox"
            checked={filter.scaledOnly}
            onChange={(e) => setFilter((f) => ({ ...f, scaledOnly: e.target.checked }))}
            className="h-4 w-4"
          />
          Scaled only
        </label>
        <label className="sr-only" htmlFor="claim-sort">
          Sort claims
        </label>
        <select
          id="claim-sort"
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as ClaimSortKey)}
          className="h-9 rounded-md border border-gray-300 bg-white px-2 text-sm dark:border-gray-700 dark:bg-gray-900"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              Sort: {o.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setSortDir((d) => (d === 1 ? -1 : 1))}
          aria-label={sortDir === 1 ? "Sort descending" : "Sort ascending"}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-300 text-sm dark:border-gray-700"
        >
          <span aria-hidden="true">{sortDir === 1 ? "↑" : "↓"}</span>
        </button>
      </div>

      {visible.length === 0 ? (
        <EmptyState
          title="No claims match the filters."
          hint="Clear the search or choose a different verdict filter."
        />
      ) : (
        <ul aria-label="Claims" className="flex flex-col gap-2">
          {visible.map((row) => {
            const selected = row.claim.id === selectedId;
            const scaled = row.verdict?.scaled || (row.scaleFactor ?? 1) < 1;
            return (
              <li key={row.claim.id}>
                <button
                  type="button"
                  onClick={() => onSelect(row.claim.id)}
                  aria-pressed={selected}
                  aria-label={`Claim ${row.claim.id}: ${row.verdict?.status ?? "no verdict yet"}`}
                  className={`flex w-full flex-col gap-1.5 rounded-lg border p-3 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 ${
                    selected
                      ? "border-blue-600 ring-1 ring-blue-600 dark:border-blue-400 dark:ring-blue-400"
                      : "border-gray-200 dark:border-gray-800"
                  }`}
                >
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
                      {row.claim.id}
                    </span>
                    {row.verdict ? (
                      <VerdictBadge status={row.verdict.status} />
                    ) : (
                      <Chip>verdict pending</Chip>
                    )}
                    {scaled && row.scaleFactor != null && (
                      <Chip aria-label={`Scaled run, scale factor ${row.scaleFactor}`}>
                        scale ×{row.scaleFactor}
                      </Chip>
                    )}
                  </span>
                  <span className="text-sm">{row.claim.text}</span>
                  <span className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-600 dark:text-gray-400">
                    <span>Reported: {formatValue(row.claim.reported_value)}</span>
                    <span>Measured: {formatValue(row.measured)}</span>
                    <span className="truncate">{row.claim.source_ref}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
