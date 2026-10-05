import { useEffect, useRef, useState } from "react";
import type { ClaimRow } from "../lib/claims";
import { formatValue } from "../lib/format";
import { cn } from "../lib/utils";
import { Button } from "./ui";

type DrawerTab = "Evidence" | "Method" | "Experiment" | "Logs";

const TABS: DrawerTab[] = ["Evidence", "Method", "Experiment", "Logs"];

interface VerdictDrawerProps {
  row: ClaimRow;
  onClose: () => void;
  onViewLogs: () => void;
}

/**
 * "Why this verdict?" side drawer. Every tab shows actual backend
 * information (evidence, config, experiment, logs); nothing is
 * fabricated.
 */
export default function VerdictDrawer({ row, onClose, onViewLogs }: VerdictDrawerProps) {
  const [tab, setTab] = useState<DrawerTab>("Evidence");
  const headingRef = useRef<HTMLHeadingElement>(null);
  const { claim, verdict, primaryEvidence } = row;

  useEffect(() => {
    headingRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const config = primaryEvidence?.config as Record<string, unknown> | undefined;

  return (
    <div className="cl-drawer-overlay fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="verdict-drawer-heading">
      <div aria-hidden="true" className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="cl-drawer absolute right-0 top-0 flex h-full w-full max-w-md flex-col gap-4 overflow-y-auto border-l border-[var(--border)] bg-[var(--surface)] p-5">
        <div className="flex items-start justify-between gap-2">
          <h2
            id="verdict-drawer-heading"
            ref={headingRef}
            tabIndex={-1}
            className="cl-h2 outline-none"
          >
            Why this verdict?
          </h2>
          <Button variant="outline" size="sm" onClick={onClose} aria-label="Close verdict details">
            Close
          </Button>
        </div>
        <p className="cl-meta">
          {claim.id} · {verdict?.status ?? "no verdict yet"}
        </p>
        <div role="tablist" aria-label="Verdict details" className="cl-tabs flex gap-1 border-b border-[var(--border)]">
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              type="button"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={cn("cl-tab", "px-2.5")}
            >
              {t}
            </button>
          ))}
        </div>
        <div role="tabpanel" className="flex flex-col gap-2 text-sm">
          {tab === "Evidence" && (
            <>
              <p className="cl-meta">Backend rationale</p>
              <p>{verdict?.rationale ?? "No backend verdict for this claim yet."}</p>
              {verdict?.reason && (
                <p className="rounded-md bg-[var(--muted-soft)] px-2 py-1 ring-1 ring-inset ring-[var(--border)]">
                  <span className="font-medium">Untestable reason: </span>
                  {verdict.reason}
                </p>
              )}
              <p className="cl-meta mt-1">Evidence ids: {verdict?.evidence_ids.join(", ") || "none"}</p>
            </>
          )}
          {tab === "Method" && (
            <>
              <p className="cl-meta">Reproduction method (sandbox record)</p>
              <p>{primaryEvidence?.method ?? "No method recorded."}</p>
              {config && Object.keys(config).length > 0 ? (
                <dl className="flex flex-col gap-1">
                  {Object.entries(config).map(([k, v]) => (
                    <div key={k} className="flex gap-2 font-mono text-xs">
                      <dt className="text-[var(--text-2)]">{k}:</dt>
                      <dd className="break-all">{JSON.stringify(v)}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="cl-meta">No configuration recorded.</p>
              )}
            </>
          )}
          {tab === "Experiment" && (
            <>
              <p className="cl-meta">Experiment record</p>
              <p>Reported: {formatValue(claim.reported_value)}</p>
              <p>Reproduced: {formatValue(row.measured)}</p>
              <p className="cl-meta">Scale factor: ×{row.scaleFactor ?? "—"}</p>
              {verdict && verdict.assumption_effects.length > 0 && (
                <ul className="flex flex-col gap-1 text-xs text-[var(--text-2)]">
                  {verdict.assumption_effects.map((e, i) => (
                    <li key={`${e.assumption_id}-${i}`}>
                      {e.alt_value} → measured {formatValue(e.measured_value)}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
          {tab === "Logs" && (
            <>
              <p className="cl-meta">Run logs</p>
              {primaryEvidence?.logs_ref ? (
                <p className="font-mono text-xs">{primaryEvidence.logs_ref}</p>
              ) : (
                <p className="cl-meta">No log reference recorded.</p>
              )}
              <div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    onClose();
                    onViewLogs();
                  }}
                >
                  View in run log
                </Button>
              </div>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
