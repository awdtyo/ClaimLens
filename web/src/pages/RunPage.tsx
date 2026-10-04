import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { artifactUrl, cancelRun } from "../api/client";
import {
  parseClaims,
  parseEvidence,
  parseParsedPaper,
  parsePlan,
  parseVerdicts,
} from "../api/models";
import { countVerdicts, joinClaimRows } from "../lib/claims";
import { formatDateTime } from "../lib/format";
import { useArtifact, useReportText, useRun } from "../hooks/useApi";
import { useCodeTree } from "../hooks/useCode";
import { claimCode, codeTreeKeys, codeZipUrl, isCodeWrittenEvent } from "../api/code";
import { useRunEvents } from "../hooks/useRunEvents";
import { Button, Card, EmptyState, ErrorState, LoadingState } from "../components/ui";
import ClaimsList from "../components/ClaimsList";
import ClaimDetail from "../components/ClaimDetail";
import LogPanel from "../components/LogPanel";
import PipelineStepper from "../components/PipelineStepper";
import ReportView from "../components/ReportView";
import TablesView from "../components/TablesView";
import VerdictBadge from "../components/VerdictBadge";
import VerdictSummary from "../components/VerdictSummary";
import { cn } from "../lib/utils";

const PaperViewer = lazy(() => import("../components/PaperViewer"));

const TERMINAL = new Set(["done", "failed", "cancelled"]);

type TabId = "results" | "claims" | "tables" | "report";

const TABS: { id: TabId; label: string }[] = [
  { id: "results", label: "Results" },
  { id: "claims", label: "Claim & paper" },
  { id: "tables", label: "Tables" },
  { id: "report", label: "Report" },
];

/**
 * Live run page: pipeline stepper driven by the SSE event stream, live
 * log, cancel, and result tabs (overview, claim/paper split view, table
 * cross-check, report).
 */
export default function RunPage() {
  const { runId } = useParams<{ runId: string }>();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<TabId>("results");
  const [selectedClaim, setSelectedClaim] = useState<string | null>(null);
  const logAnchorRef = useRef<HTMLDivElement>(null);

  // Poll first for state; SSE drives the live log (replay included).
  const runQuery = useRun(runId);
  const run = runQuery.data;
  const active = run ? !TERMINAL.has(run.status) : true;
  const finished = run ? TERMINAL.has(run.status) : false;

  // Always subscribe: the backend replays stored events from the start,
  // so finished runs still show their full log without reconnect loops.
  const { events, connected, retries, complete } = useRunEvents(runId);

  const claimsQuery = useArtifact(runId, "claims", parseClaims, true);
  // Verdicts, evidence and plan load once finished, or eagerly when a
  // tab needs them during a live run.
  const wantResults = finished || tab === "results" || tab === "claims" || tab === "report";
  const verdictsQuery = useArtifact(runId, "verdicts", parseVerdicts, wantResults);
  const evidenceQuery = useArtifact(runId, "evidence", parseEvidence, wantResults);
  const planQuery = useArtifact(runId, "plan", parsePlan, wantResults);
  const parsedQuery = useArtifact(runId, "parsed", parseParsedPaper, true);
  const reportQuery = useReportText(runId, finished || tab === "report");
  const codeTreeQuery = useCodeTree(runId, true);

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
  const selectedRow = rows.find((r) => r.claim.id === selectedClaim) ?? rows[0] ?? null;

  const scrollToLog = () => {
    setTab("results");
    requestAnimationFrame(() => {
      document.getElementById("run-log")?.focus();
      logAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
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
        title="Could not load this run."
        message="The backend did not answer or the run does not exist."
        onRetry={() => void runQuery.refetch()}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
            ← All runs
          </Link>
          <h1 className="mt-1 break-all text-xl font-semibold tracking-tight">
            {run.filename || runId}
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Status: {run.status} · created {formatDateTime(run.created_at)}
            {run.demo && " · demo"}
          </p>
          {run.error && (
            <p role="alert" className="mt-1 text-sm text-red-700 dark:text-red-300">
              {run.error}
            </p>
          )}
        </div>
        {active && (
          <Button
            variant="destructive"
            disabled={cancelMutation.isPending}
            onClick={() => cancelMutation.mutate()}
          >
            {cancelMutation.isPending ? "Cancelling…" : "Cancel run"}
          </Button>
        )}
      </div>

      <Card className="p-4" aria-label="Pipeline progress">
        <PipelineStepper run={run} />
      </Card>

      <div ref={logAnchorRef}>
        <LogPanel events={events} connected={connected} retries={retries} complete={complete} />
      </div>

      <div role="tablist" aria-label="Run results" className="flex flex-wrap gap-1 border-b border-gray-200 dark:border-gray-800">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            type="button"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "rounded-t-md px-4 py-2 text-sm font-medium",
              tab === t.id
                ? "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100"
                : "text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800/50",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {tab === "results" && (
          <div className="flex flex-col gap-4">
            {verdictsQuery.isLoading && !finished ? (
              <EmptyState
                title="Results are not ready yet."
                hint="Verdicts appear here once the verify stage finishes. Watch the live log above."
              />
            ) : verdictsQuery.isError ? (
              <ErrorState
                title="Could not load verdicts."
                message="The verdicts artifact is not ready yet, or the backend did not answer."
                onRetry={() => void verdictsQuery.refetch()}
              />
            ) : (
              <>
                {finished && verdictsQuery.data && (
                  <VerdictSummary counts={counts} />
                )}
                {claimsQuery.isLoading ? (
                  <LoadingState label="Loading claims…" />
                ) : claimsQuery.isError || !claimsQuery.data ? (
                  <ErrorState
                    title="Could not load claims."
                    message="The claims artifact is not ready yet, or the backend did not answer."
                    onRetry={() => void claimsQuery.refetch()}
                  />
                ) : (
                  <ClaimsList
                    rows={rows}
                    selectedId={selectedRow?.claim.id ?? null}
                    onSelect={(id) => {
                      setSelectedClaim(id);
                      setTab("claims");
                    }}
                  />
                )}
              </>
            )}
          </div>
        )}

        {tab === "claims" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <Suspense fallback={<LoadingState label="Loading paper viewer…" />}>
              <PaperViewer
                pdfUrl={artifactUrl(runId, "paper")}
                targetPage={selectedRow?.claim.page ?? null}
              />
            </Suspense>
            <Card className="h-fit p-4">
              {claimsQuery.isLoading ? (
                <LoadingState label="Loading claims…" />
              ) : rows.length === 0 ? (
                <EmptyState
                  title="No claims yet."
                  hint="Claims appear here once the claims stage finishes."
                />
              ) : selectedRow ? (
                <>
                  <label className="sr-only" htmlFor="claim-select">
                    Select a claim
                  </label>
                  <select
                    id="claim-select"
                    value={selectedRow.claim.id}
                    onChange={(e) => setSelectedClaim(e.target.value)}
                    className="mb-3 h-9 w-full rounded-md border border-gray-300 bg-white px-2 text-sm dark:border-gray-700 dark:bg-gray-900"
                  >
                    {rows.map((r) => (
                      <option key={r.claim.id} value={r.claim.id}>
                        {r.claim.id}: {r.claim.text.slice(0, 80)}
                      </option>
                    ))}
                  </select>
                  <ClaimDetail
                    row={selectedRow}
                    assumptions={planQuery.data?.assumptions ?? []}
                    onViewLogs={scrollToLog}
                    runId={runId}
                    codeClaim={
                      codeTreeQuery.data
                        ? claimCode(codeTreeQuery.data, selectedRow.claim.id)
                        : null
                    }
                    treeLoading={codeTreeQuery.isLoading}
                    treeError={codeTreeQuery.isError}
                    onRetryTree={() => void codeTreeQuery.refetch()}
                    runFailed={run?.status === "failed"}
                    newFiles={newCodeFiles}
                  />
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <a
                      href={codeZipUrl(runId)}
                      download
                      className="inline-flex h-9 items-center rounded-md border border-gray-300 px-3 text-sm font-medium hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
                    >
                      Download code
                    </a>
                    <span className="text-xs text-gray-600 dark:text-gray-400">
                      Archive of the exact code that was executed.
                    </span>
                  </div>
                  {selectedRow.verdict == null && (
                    <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                      No backend verdict for this claim yet.
                    </p>
                  )}
                </>
              ) : null}
            </Card>
          </div>
        )}

        {tab === "tables" && (
          parsedQuery.isLoading ? (
            <LoadingState label="Loading tables…" />
          ) : parsedQuery.isError || !parsedQuery.data ? (
            <ErrorState
              title="Could not load tables."
              message="The ingest artifact is not ready yet, or the backend did not answer."
              onRetry={() => void parsedQuery.refetch()}
            />
          ) : (
            <TablesView parsed={parsedQuery.data} />
          )
        )}

        {tab === "report" && (
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
        )}
      </div>

      {finished && rows.length > 0 && (
        <section aria-label="All verdicts" className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold">All verdicts</h2>
          <ul className="flex flex-col gap-1 text-sm">
            {rows.map((row) => (
              <li key={row.claim.id} className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs">{row.claim.id}</span>
                {row.verdict ? (
                  <VerdictBadge status={row.verdict.status} />
                ) : (
                  <span className="text-gray-500">verdict pending</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
