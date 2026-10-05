import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { artifactUrl, cancelRun } from "../api/client";
import {
  parseClaims,
  parseEvidence,
  parseParsedPaper,
  parsePlan,
  parseVerdicts,
} from "../api/models";
import { countVerdicts, joinClaimRows } from "../lib/claims";
import { useArtifact, useReportText, useRun } from "../hooks/useApi";
import { useCodeTree } from "../hooks/useCode";
import { claimCode, codeTreeKeys, isCodeWrittenEvent } from "../api/code";
import { useRunEvents } from "../hooks/useRunEvents";
import { Button, EmptyState, ErrorState, LoadingState } from "../components/ui";
import AuditHeader from "../components/AuditHeader";
import AuditSidebar, { type AuditSection } from "../components/AuditSidebar";
import ClaimTable from "../components/ClaimTable";
import CodeTab from "../components/CodeTab";
import EvidencePanel from "../components/EvidencePanel";
import FindingsList from "../components/FindingsList";
import LogPanel from "../components/LogPanel";
import PipelineStepper from "../components/PipelineStepper";
import ProcessingStatus from "../components/ProcessingStatus";
import ReportView from "../components/ReportView";
import TablesView from "../components/TablesView";
import VerdictDrawer from "../components/VerdictDrawer";
import VerdictSummary from "../components/VerdictSummary";
import { ExperimentInspector, ReproducibilityCapsule, ProvenanceTrail } from "../components/lab";

const PaperViewer = lazy(() => import("../components/PaperViewer"));

const TERMINAL = new Set(["done", "failed", "cancelled"]);

const FILTERS = [
  { id: "all", label: "All" },
  { id: "replicated", label: "Verified" },
  { id: "partially replicated", label: "Partial" },
  { id: "not replicated", label: "Contradicted" },
  { id: "untestable", label: "Inconclusive" },
] as const;

type FilterId = (typeof FILTERS)[number]["id"];

/**
 * Audit workspace: three-column investigation layout (sidebar, claim
 * workspace, evidence inspector) driven by real backend state. The
 * layout collapses to drawers and stacked views on smaller screens.
 */
export default function RunPage() {
  const { runId } = useParams<{ runId: string }>();
  const queryClient = useQueryClient();
  const [section, setSection] = useState<AuditSection>("claims");
  const [selectedClaim, setSelectedClaim] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterId>("all");
  const [navOpen, setNavOpen] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [investigationOpen, setInvestigationOpen] = useState(false);
  const logAnchorRef = useRef<HTMLDivElement>(null);

  // Poll first for state; SSE drives the live log (replay included).
  const runQuery = useRun(runId);
  const run = runQuery.data;
  const active = run ? !TERMINAL.has(run.status) : true;
  const finished = run ? TERMINAL.has(run.status) : false;

  // Always subscribe: the backend replays stored events from the start,
  // so finished runs still show their full log without reconnect loops.
  const { events, connected, retries, complete } = useRunEvents(runId);

  const needResults =
    finished || section === "overview" || section === "claims" || section === "evidence" || section === "experiments" || section === "run-history" || section === "environment" || section === "parameters" || section === "provenance";
  const claimsQuery = useArtifact(runId, "claims", parseClaims, true);
  const verdictsQuery = useArtifact(runId, "verdicts", parseVerdicts, needResults);
  const evidenceQuery = useArtifact(runId, "evidence", parseEvidence, needResults);
  const planQuery = useArtifact(runId, "plan", parsePlan, needResults);
  const parsedQuery = useArtifact(runId, "parsed", parseParsedPaper, true);
  const reportQuery = useReportText(runId, finished || section === "overview");
  const codeTreeQuery = useCodeTree(runId, section === "experiments" || active);

  // Live code updates: refetch the file tree when code_written events
  // arrive, without touching selection, focus or scroll position. New
  // files get a "new" indicator in the Code tab.
  const [newCodeFiles, setNewCodeFiles] = useState<Set<string>>(new Set());
  const prevCodeKeysRef = useRef<Set<string> | null>(null);
  const seenEventsRef = useRef(0);
  useEffect(() => {
    if (!codeTreeQuery.data) return;
    const keys = codeTreeKeys(codeTreeQuery.data);
    const prev = prevCodeKeysRef.current;
    if (prev === null) {
      prevCodeKeysRef.current = keys;
      return;
    }
    const added = [...keys].filter((k) => !prev.has(k));
    if (added.length > 0) {
      setNewCodeFiles((old) => new Set([...old, ...added]));
    }
    prevCodeKeysRef.current = keys;
  }, [codeTreeQuery.data]);
  useEffect(() => {
    if (!active) {
      seenEventsRef.current = events.length;
      return;
    }
    const fresh = events.slice(seenEventsRef.current);
    seenEventsRef.current = events.length;
    if (fresh.some(isCodeWrittenEvent)) {
      void codeTreeQuery.refetch();
    }
    // Refetch only on new events; tree data drives the "new" markers.
  }, [events, active]);

  const cancelMutation = useMutation({
    mutationFn: () => cancelRun(runId as string),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["run", runId] });
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });

  const rows = useMemo(() => {
    if (!claimsQuery.data) return [];
    return joinClaimRows(
      claimsQuery.data,
      verdictsQuery.data ?? [],
      evidenceQuery.data ?? [],
    );
  }, [claimsQuery.data, verdictsQuery.data, evidenceQuery.data]);

  const counts = useMemo(() => countVerdicts(rows), [rows]);
  const visibleRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (filter !== "all") {
        const bucket =
          r.verdict?.status.trim().toLowerCase() === "untestable at this scale"
            ? "untestable"
            : (r.verdict?.status.trim().toLowerCase() ?? "untestable");
        if (bucket !== filter) return false;
      }
      if (q && !`${r.claim.id} ${r.claim.text} ${r.claim.source_ref}`.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });
  }, [rows, query, filter]);

  const selectedIndex = rows.findIndex((r) => r.claim.id === (selectedClaim ?? rows[0]?.claim.id));
  const selectedRow = (selectedIndex >= 0 ? rows[selectedIndex] : rows[0]) ?? null;

  const reproduced = rows.filter((r) => r.measured !== null).length;
  const coverage = rows.length > 0 ? Math.round((reproduced / rows.length) * 100) : 0;
  const badges = useMemo(
    () => [...new Set(rows.map((r) => r.claim.metric).filter((m): m is string => Boolean(m)))],
    [rows],
  );

  const scrollToLog = () => {
    setSection("logs");
    requestAnimationFrame(() => {
      document.getElementById("run-log")?.focus();
      logAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  };

  const selectSection = (s: AuditSection) => {
    setSection(s);
    setNavOpen(false);
  };

  const selectClaim = (id: string) => {
    setSelectedClaim(id);
  };

  if (!runId) {
    return (
      <ErrorState title="Missing run id." message="No run was specified in the URL." />
    );
  }

  if (runQuery.isLoading) return <LoadingState label="Loading run…" />;
  if (runQuery.isError || !run) {
    return (
      <ErrorState
        title="Unable to connect to audit server"
        message="Check your connection and retry."
        onRetry={() => void runQuery.refetch()}
      />
    );
  }

  const planItems = planQuery.data?.items ?? [];
  const assumptions = planQuery.data?.assumptions ?? [];

  return (
    <div className="flex flex-col gap-4">
      <AuditHeader
        runId={runId}
        run={run}
        title={parsedQuery.data?.title ?? ""}
        badges={badges}
      />

      {/* Mobile section switcher */}
      <div className="flex gap-2 min-[901px]:hidden">
        <Button variant="outline" size="sm" onClick={() => setNavOpen(true)} aria-haspopup="dialog">
          ☰ Audit Sections
        </Button>
        <Button variant="outline" size="sm" onClick={() => setEvidenceOpen(true)} aria-haspopup="dialog">
          View Evidence
        </Button>
        {active && (
          <Button
            variant="destructive"
            size="sm"
            disabled={cancelMutation.isPending}
            onClick={() => cancelMutation.mutate()}
            className="ml-auto"
          >
            {cancelMutation.isPending ? "Cancelling…" : "Cancel run"}
          </Button>
        )}
      </div>

      {active && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0 flex-1" />
          <Button
            variant="destructive"
            size="sm"
            disabled={cancelMutation.isPending}
            onClick={() => cancelMutation.mutate()}
            className="max-[900px]:hidden"
          >
            {cancelMutation.isPending ? "Cancelling…" : "Cancel run"}
          </Button>
        </div>
      )}

      <div className="audit-workspace items-start">
        {/* Left sidebar */}
        <aside className="audit-sidebar-col audit-scroll cl-surface top-4 p-3 min-[901px]:sticky">
          <AuditSidebar active={section} status={run.status} onSelect={selectSection} />
        </aside>

        {/* Main claim workspace */}
        <div className="audit-scroll min-w-0 pr-0.5">
          {section === "overview" && (
            <div className="flex flex-col gap-4">
              {active && <ProcessingStatus run={run} />}
              <section aria-labelledby="ws-metrics" className="flex flex-col gap-2">
                <h2 id="ws-metrics" className="cl-h2">Audit summary</h2>
                <dl aria-label="Audit metrics" className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                  <MetricCard label="Claims" value={rows.length} />
                  <MetricCard label="Verified" value={counts.replicated} />
                  <MetricCard label="Partial" value={counts["partially replicated"]} />
                  <MetricCard label="Inconclusive" value={counts.untestable} />
                  <MetricCard label="Coverage" value={rows.length > 0 ? `${coverage}%` : "—"} />
                </dl>
                {finished && verdictsQuery.data && <VerdictSummary counts={counts} />}
              </section>
              <section aria-label="Pipeline progress" className="cl-surface p-4">
                <PipelineStepper run={run} />
              </section>
              <ReportView
                runId={runId}
                report={reportQuery.data}
                isLoading={reportQuery.isLoading}
                isError={reportQuery.isError}
                onRetry={() => void reportQuery.refetch()}
                jsonBundle={
                  claimsQuery.data && verdictsQuery.data
                    ? {
                        run_id: runId,
                        claims: claimsQuery.data,
                        verdicts: verdictsQuery.data,
                        evidence: evidenceQuery.data ?? [],
                        plan: planQuery.data ?? null,
                      }
                    : null
                }
              />
            </div>
          )}

          {section === "claims" && (
            <div className="flex flex-col gap-3">
              <div>
                <h2 className="cl-h2">Claims</h2>
                <p className="cl-meta mt-0.5">
                  {rows.length} claim{rows.length === 1 ? "" : "s"} identified ·{" "}
                  {counts.replicated} Verified · {counts["partially replicated"]} Partial ·{" "}
                  {counts["not replicated"]} Contradicted · {counts.untestable} Inconclusive
                </p>
              </div>
              <section aria-label="Reproduction coverage" className="flex flex-col gap-1.5">
                <div className="flex items-baseline justify-between gap-2">
                  <h3 className="cl-meta font-semibold uppercase tracking-[0.1em]">
                    Reproduction coverage
                  </h3>
                  <span className="font-mono text-xs">{coverage}%</span>
                </div>
                <div className="cl-progress" role="progressbar" aria-valuenow={coverage} aria-valuemin={0} aria-valuemax={100} aria-label="Reproduction coverage">
                  <span style={{ width: `${coverage}%` }} />
                </div>
                <p className="cl-meta">
                  {reproduced} of {rows.length} claims reproduced
                </p>
              </section>
              <div className="flex flex-col gap-2">
                <label className="sr-only" htmlFor="claim-search">Search claims</label>
                <input
                  id="claim-search"
                  type="search"
                  placeholder="Search claims…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="h-9 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 text-sm"
                />
                <div role="group" aria-label="Filter by verdict" className="flex flex-wrap gap-1.5">
                  {FILTERS.map((f) => (
                    <button
                      key={f.id}
                      type="button"
                      aria-pressed={filter === f.id}
                      onClick={() => setFilter(f.id)}
                      className={
                        filter === f.id
                          ? "rounded-full bg-[var(--accent)] px-2.5 py-1 text-xs font-medium text-[var(--accent-ink)]"
                          : "rounded-full border border-[var(--border)] px-2.5 py-1 text-xs text-[var(--text-2)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                      }
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>
              {claimsQuery.isLoading ? (
                <LoadingState label="Loading claims…" />
              ) : claimsQuery.isError || !claimsQuery.data ? (
                <ErrorState
                  title="Could not load claims."
                  message="The claims artifact is not ready yet, or the backend did not answer."
                  onRetry={() => void claimsQuery.refetch()}
                />
              ) : visibleRows.length === 0 ? (
                <EmptyState
                  title="No claims match the filters."
                  hint="Clear the search or choose a different verdict filter."
                />
              ) : (
                <ClaimTable
                  rows={visibleRows}
                  selectedId={selectedRow?.claim.id ?? null}
                  onSelect={selectClaim}
                />
              )}
              <div className="md:hidden">
                <Button variant="outline" size="sm" onClick={() => setEvidenceOpen(true)} className="w-full">
                  View Evidence
                </Button>
              </div>
            </div>
          )}

          {section === "evidence" && (
            <div className="flex flex-col gap-3">
              <h2 className="cl-h2">Evidence</h2>
              {selectedRow?.verdict ? (
                <FindingsList
                  findings={selectedRow.verdict.code_findings ?? []}
                  verdictStatus={selectedRow.verdict.status}
                  onOpenFile={() => {
                    setSection("experiments");
                  }}
                />
              ) : (
                <EmptyState
                  title="No evidence yet."
                  hint="Evidence appears here once the sandbox and verify stages finish."
                />
              )}
            </div>
          )}

          {section === "experiments" && (
            <div className="flex flex-col gap-3">
              {selectedRow ? (
                <ExperimentInspector
                  runId={runId}
                  claimId={selectedRow.claim.id}
                  evidence={
                    evidenceQuery.data?.find((e) => e.claim_id === selectedRow.claim.id) ?? null
                  }
                  planItem={
                    planQuery.data?.items.find((p) => p.claim_id === selectedRow.claim.id) ?? null
                  }
                  verdict={selectedRow.verdict ?? null}
                />
              ) : (
                <>
                  <ExperimentInspector
                    runId={runId}
                    claimId={null}
                    evidence={null}
                    planItem={null}
                    verdict={null}
                  />
                  <EmptyState
                    title="No claim selected."
                    hint="Select a claim in the Claims section to see its experiment details."
                  />
                </>
              )}
            </div>
          )}

          {/* Run history — full code iteration view */}
          {section === "run-history" && (
            <div className="flex flex-col gap-3">
              {selectedRow ? (
                <CodeTab
                  runId={runId}
                  claimId={selectedRow.claim.id}
                  codeClaim={
                    codeTreeQuery.data ? claimCode(codeTreeQuery.data, selectedRow.claim.id) : null
                  }
                  treeLoading={codeTreeQuery.isLoading}
                  treeError={codeTreeQuery.isError}
                  onRetryTree={() => void codeTreeQuery.refetch()}
                  runFailed={run.status === "failed"}
                  newFiles={newCodeFiles}
                />
              ) : (
                <EmptyState
                  title="No claim selected."
                  hint="Select a claim in the Claims section first."
                />
              )}
            </div>
          )}

          {/* Environment panel */}
          {section === "environment" && (
            <div className="flex flex-col gap-3">
              <h2 className="cl-h2">Environment</h2>
              <p className="cl-meta">Execution environment for sandboxed experiments.</p>
              <div className="cl-surface p-4 flex flex-col gap-3">
                {[
                  { label: "Runtime",    value: "Python 3.11" },
                  { label: "Framework",  value: "PyTorch" },
                  { label: "Container",  value: "Docker" },
                  { label: "GPU",        value: "CUDA (when available)" },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center gap-3 border-b border-[var(--border)] pb-2 last:border-0 last:pb-0">
                    <span className="cl-meta w-24 shrink-0">{label}</span>
                    <span className="font-mono text-sm">{value}</span>
                  </div>
                ))}
              </div>
              <ReproducibilityCapsule
                data
                code
                environment
                parameters={!!(planQuery.data?.items.length)}
                seed={false}
                result={!!(evidenceQuery.data?.some((e) => e.measured_value != null))}
              />
            </div>
          )}

          {/* Parameters panel */}
          {section === "parameters" && (
            <div className="flex flex-col gap-3">
              <h2 className="cl-h2">Parameters</h2>
              <p className="cl-meta">Reproduction configuration from the backend plan.</p>
              {planQuery.isLoading ? (
                <LoadingState label="Loading plan…" />
              ) : planQuery.isError || !planQuery.data ? (
                <ErrorState
                  title="Could not load parameters."
                  message="The plan artifact is not ready yet."
                  onRetry={() => void planQuery.refetch()}
                />
              ) : planItems.length === 0 ? (
                <EmptyState title="No parameters yet." hint="Parameters appear once the plan stage finishes." />
              ) : (
                <ol className="flex flex-col gap-2">
                  {planItems.map((item) => (
                    <li key={item.claim_id} className="cl-surface p-3">
                      <p className="cl-mono text-xs text-[var(--text-2)]">
                        {item.claim_id} · scale ×{item.scale_factor}
                      </p>
                      <ul className="mt-1 flex list-disc flex-col gap-0.5 pl-5 text-sm">
                        {item.steps.map((step, i) => (
                          <li key={i}>{step}</li>
                        ))}
                      </ul>
                      {item.config && (
                        <pre className="cl-mono mt-2 text-xs text-[var(--text-2)] overflow-auto bg-[var(--surface-2)] rounded p-2">
                          {JSON.stringify(item.config, null, 2)}
                        </pre>
                      )}
                    </li>
                  ))}
                </ol>
              )}
              {assumptions.length > 0 && (
                <section aria-label="Assumptions" className="flex flex-col gap-2">
                  <h3 className="text-sm font-semibold">Assumptions ({assumptions.length})</h3>
                  <ul className="flex flex-col gap-2">
                    {assumptions.map((a) => (
                      <li key={a.id} className="cl-surface p-3 text-sm">
                        <p className="font-medium">{a.detail}</p>
                        <p className="cl-meta mt-0.5">
                          Chose: {a.value_chosen}. {a.reason} ({a.confidence} confidence)
                        </p>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          )}

          {/* Provenance panel */}
          {section === "provenance" && (
            <div className="flex flex-col gap-3">
              <h2 className="cl-h2">Provenance</h2>
              <p className="cl-meta">Experiment lineage — paper → claim → experiment → result → verdict.</p>
              <ProvenanceTrail
                runId={runId}
                claimId={selectedRow?.claim.id}
                filename={parsedQuery.data?.title ?? undefined}
                demo={!selectedRow}
              />
              {!selectedRow && (
                <p className="cl-meta text-sm">
                  Select a claim in the Claims section to see full provenance.
                </p>
              )}
            </div>
          )}

          {section === "logs" && (
            <div ref={logAnchorRef} className="flex flex-col gap-3">
              <h2 className="cl-h2">Logs</h2>
              <LogPanel events={events} connected={connected} retries={retries} complete={complete} />
            </div>
          )}

          {section === "paper" && (
            <div className="flex flex-col gap-3">
              <h2 className="cl-h2">Paper</h2>
              <Suspense fallback={<LoadingState label="Loading paper viewer…" />}>
                <PaperViewer
                  pdfUrl={artifactUrl(runId, "paper")}
                  targetPage={selectedRow?.claim.page ?? null}
                />
              </Suspense>
            </div>
          )}

          {section === "methods" && (
            <div className="flex flex-col gap-3">
              <h2 className="cl-h2">Methods</h2>
              <p className="cl-meta">Reproduction steps from the backend plan.</p>
              {planQuery.isLoading ? (
                <LoadingState label="Loading plan…" />
              ) : planQuery.isError || !planQuery.data ? (
                <ErrorState
                  title="Could not load methods."
                  message="The plan artifact is not ready yet, or the backend did not answer."
                  onRetry={() => void planQuery.refetch()}
                />
              ) : planItems.length === 0 ? (
                <EmptyState title="No methods yet." hint="Reproduction steps appear once the plan stage finishes." />
              ) : (
                <ol className="flex flex-col gap-2">
                  {planItems.map((item) => (
                    <li key={item.claim_id} className="cl-surface p-3">
                      <p className="cl-mono text-xs text-[var(--text-2)]">
                        {item.claim_id} · scale ×{item.scale_factor}
                      </p>
                      <ul className="mt-1 flex list-disc flex-col gap-0.5 pl-5 text-sm">
                        {item.steps.map((step, i) => (
                          <li key={i}>{step}</li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ol>
              )}
              {assumptions.length > 0 && (
                <section aria-label="Assumptions" className="flex flex-col gap-2">
                  <h3 className="text-sm font-semibold">Assumptions ({assumptions.length})</h3>
                  <ul className="flex flex-col gap-2">
                    {assumptions.map((a) => (
                      <li key={a.id} className="cl-surface p-3 text-sm">
                        <p className="font-medium">{a.detail}</p>
                        <p className="cl-meta mt-0.5">
                          Chose: {a.value_chosen}. {a.reason} ({a.confidence} confidence)
                        </p>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          )}

          {section === "datasets" && (
            <div className="flex flex-col gap-3">
              <h2 className="cl-h2">Datasets</h2>
              <p className="cl-meta">Experiment records from the backend sandbox.</p>
              {evidenceQuery.isLoading ? (
                <LoadingState label="Loading experiments…" />
              ) : evidenceQuery.isError || !evidenceQuery.data ? (
                <ErrorState
                  title="Could not load datasets."
                  message="The evidence artifact is not ready yet, or the backend did not answer."
                  onRetry={() => void evidenceQuery.refetch()}
                />
              ) : evidenceQuery.data.length === 0 ? (
                <EmptyState title="No datasets yet." hint="Experiment records appear once the sandbox stage finishes." />
              ) : (
                <ul className="cl-surface divide-y divide-[var(--border)] overflow-hidden !p-0">
                  {evidenceQuery.data.map((e) => (
                    <li key={e.id} className="px-4 py-3">
                      <p className="cl-mono text-xs text-[var(--text-2)]">
                        {e.id} · {e.claim_id} · scale ×{e.scale_factor}
                      </p>
                      <p className="mt-0.5 text-sm">{e.method}</p>
                      <p className="cl-meta mt-0.5">
                        Measured: {e.measured_value ?? "n/a"}
                        {e.logs_ref ? ` · Log: ${e.logs_ref}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {section === "results" && (
            <div className="flex flex-col gap-3">
              <h2 className="cl-h2">Results</h2>
              {parsedQuery.isLoading ? (
                <LoadingState label="Loading tables…" />
              ) : parsedQuery.isError || !parsedQuery.data ? (
                <ErrorState
                  title="Could not load tables."
                  message="The ingest artifact is not ready yet, or the backend did not answer."
                  onRetry={() => void parsedQuery.refetch()}
                />
              ) : (
                <TablesView parsed={parsedQuery.data} />
              )}
            </div>
          )}
        </div>

        {/* Right evidence inspector */}
        <aside className="audit-evidence-col audit-scroll min-[901px]:sticky min-[901px]:top-4" aria-label="Evidence inspector">
          <EvidencePanel
            row={selectedRow}
            index={selectedIndex >= 0 ? selectedIndex : null}
            onViewFull={() => setInvestigationOpen(true)}
          />
        </aside>
      </div>

      {/* Mobile audit nav drawer */}
      {navOpen && (
        <div className="cl-drawer-overlay fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Audit sections">
          <div aria-hidden="true" className="absolute inset-0 bg-black/30" onClick={() => setNavOpen(false)} />
          <div className="cl-left-drawer absolute left-0 top-0 h-full w-72 max-w-[85vw] overflow-y-auto border-r border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold">Audit Sections</p>
              <Button variant="outline" size="sm" onClick={() => setNavOpen(false)} aria-label="Close audit sections">
                Close
              </Button>
            </div>
            <AuditSidebar active={section} status={run.status} onSelect={selectSection} />
          </div>
        </div>
      )}

      {/* Mobile evidence bottom sheet */}
      {evidenceOpen && (
        <div className="cl-sheet-overlay fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Evidence">
          <div aria-hidden="true" className="absolute inset-0 bg-black/30" onClick={() => setEvidenceOpen(false)} />
          <div className="cl-sheet absolute inset-x-0 bottom-0 max-h-[85vh] overflow-y-auto rounded-t-2xl border-t border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold">Evidence</p>
              <Button variant="outline" size="sm" onClick={() => setEvidenceOpen(false)} aria-label="Close evidence">
                Close
              </Button>
            </div>
            <EvidencePanel
              row={selectedRow}
              index={selectedIndex >= 0 ? selectedIndex : null}
              onViewFull={() => {
                setEvidenceOpen(false);
                setInvestigationOpen(true);
              }}
            />
          </div>
        </div>
      )}

      {/* Claim investigation drawer */}
      {investigationOpen && selectedRow && (
        <VerdictDrawer
          row={selectedRow}
          onClose={() => setInvestigationOpen(false)}
          onViewLogs={scrollToLog}
        />
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="cl-surface flex flex-col gap-0.5 px-3 py-2.5">
      <dt className="cl-meta">{label}</dt>
      <dd className="text-xl font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
