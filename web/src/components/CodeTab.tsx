import { useEffect, useMemo, useRef, useState } from "react";
import type { CodeClaim } from "../api/code";
import { diffLines } from "../lib/diff";
import { cn } from "../lib/utils";
import { useCodeFile } from "../hooks/useCode";
import CodeViewer from "./CodeViewer";
import { EmptyState, ErrorState, LoadingState } from "./ui";

export interface HighlightRequest {
  file: string;
  line: number | null;
}

interface CodeTabProps {
  runId: string;
  claimId: string;
  codeClaim: CodeClaim | null;
  treeLoading: boolean;
  treeError: boolean;
  onRetryTree: () => void;
  runFailed: boolean;
  /** Files seen as new since the tab was opened (`claim/iter/index`). */
  newFiles?: Set<string>;
  /** External request to jump to a file+line (e.g. from a finding). */
  highlightRequest?: HighlightRequest | null;
  onHighlightConsumed?: () => void;
}

function fileKey(claimId: string, iteration: number, index: number): string {
  return `${claimId}/${iteration}/${index}`;
}

/**
 * Code tab: iteration selector, file tree per iteration, read-only
 * viewer and diff between iterations. Files load on demand by
 * server-assigned index; selection is preserved across live tree
 * refreshes so reading position is never lost.
 */
export default function CodeTab({
  runId,
  claimId,
  codeClaim,
  treeLoading,
  treeError,
  onRetryTree,
  runFailed,
  newFiles,
  highlightRequest,
  onHighlightConsumed,
}: CodeTabProps) {
  const iterations = useMemo(
    () => [...(codeClaim?.iterations ?? [])].sort((a, b) => a.iteration - b.iteration),
    [codeClaim],
  );
  const [iteration, setIteration] = useState<number | null>(null);
  const [fileIndex, setFileIndex] = useState<number>(0);
  const [highlightLine, setHighlightLine] = useState<number | null>(null);
  const [diffMode, setDiffMode] = useState(false);
  const [compareIteration, setCompareIteration] = useState<number | null>(null);
  const treeRef = useRef<HTMLDivElement>(null);

  // Default to the latest iteration without stealing an existing selection.
  useEffect(() => {
    if (iterations.length === 0) return;
    setIteration((prev) => {
      if (prev !== null && iterations.some((it) => it.iteration === prev)) {
        return prev;
      }
      return iterations[iterations.length - 1].iteration;
    });
    setCompareIteration((prev) => {
      if (prev !== null && iterations.some((it) => it.iteration === prev)) {
        return prev;
      }
      return iterations.length > 1 ? iterations[iterations.length - 2].iteration : null;
    });
  }, [iterations]);

  const activeIter = iterations.find((it) => it.iteration === iteration) ?? null;
  const files = activeIter?.files ?? [];

  // Keep the file selection valid when the tree refreshes live.
  useEffect(() => {
    if (fileIndex >= files.length) setFileIndex(0);
  }, [files.length, fileIndex]);

  // Jump to a file+line requested from outside (finding link).
  useEffect(() => {
    if (!highlightRequest || iterations.length === 0) return;
    let targetIter = iteration;
    let targetIt = activeIter;
    for (const it of iterations) {
      const idx = it.files.findIndex((f) => f.name === highlightRequest.file);
      if (idx >= 0) {
        targetIter = it.iteration;
        targetIt = it;
        setIteration(it.iteration);
        setFileIndex(idx);
        break;
      }
    }
    if (targetIt) {
      setHighlightLine(highlightRequest.line);
      setDiffMode(false);
    }
    onHighlightConsumed?.();
    // Scroll the highlighted line into view without moving overall focus.
    requestAnimationFrame(() => {
      const line = highlightRequest.line;
      const el =
        line != null
          ? document.getElementById(`code-${claimId}-${targetIter}-${line}-L${line}`)
          : null;
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    // Only react to new requests.
  }, [highlightRequest]);

  const fileQuery = useCodeFile(
    runId,
    claimId,
    iteration,
    files.length > 0 ? fileIndex : null,
    files.length > 0,
  );

  const selectedFile = files[fileIndex] ?? null;
  const anchorPrefix = `code-${claimId}-${iteration}-${fileIndex}`;

  const compareIter = iterations.find((it) => it.iteration === compareIteration) ?? null;
  const compareFileIndex = compareIter
    ? compareIter.files.findIndex((f) => f.name === selectedFile?.name)
    : -1;
  const compareQuery = useCodeFile(
    runId,
    claimId,
    compareIteration,
    compareFileIndex >= 0 ? compareFileIndex : null,
    diffMode && compareFileIndex >= 0,
  );

  const diffRows = useMemo(() => {
    if (!diffMode) return null;
    if (!fileQuery.data || !compareQuery.data) return null;
    if (fileQuery.data.binary || compareQuery.data.binary) return null;
    return diffLines(compareQuery.data.text, fileQuery.data.text);
  }, [diffMode, fileQuery.data, compareQuery.data]);

  if (treeLoading) return <LoadingState label="Loading code…" />;
  if (treeError) {
    return (
      <ErrorState
        title="Could not load code."
        message="The code tree is not ready yet, or the backend did not answer."
        onRetry={onRetryTree}
      />
    );
  }
  if (!codeClaim || iterations.length === 0) {
    return (
      <EmptyState
        title={runFailed ? "Run failed before code was written." : "No code yet."}
        hint={
          runFailed
            ? "This claim has no saved code. Partial output, if any, appears above."
            : "Code appears here once the agent writes it during the sandbox stage."
        }
      />
    );
  }

  const onTreeKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const next =
      e.key === "ArrowDown"
        ? Math.min(fileIndex + 1, files.length - 1)
        : Math.max(fileIndex - 1, 0);
    setFileIndex(next);
    setHighlightLine(null);
  };

  return (
    <div className="flex flex-col gap-3">
      <p role="note" className="text-xs text-gray-600 dark:text-gray-400">
        This is the exact code that was executed. The agent never saw the
        paper&apos;s reported numbers (a blinded run).
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <label className="text-xs text-gray-600 dark:text-gray-400" htmlFor={`iter-select-${claimId}`}>
          Iteration
        </label>
        <select
          id={`iter-select-${claimId}`}
          value={iteration ?? ""}
          onChange={(e) => {
            setIteration(Number(e.target.value));
            setFileIndex(0);
            setHighlightLine(null);
            setDiffMode(false);
          }}
          className="h-9 rounded-md border border-gray-300 bg-white px-2 text-sm dark:border-gray-700 dark:bg-gray-900"
        >
          {iterations.map((it) => (
            <option key={it.iteration} value={it.iteration}>
              Iteration {it.iteration} ({it.files.length} file{it.files.length === 1 ? "" : "s"})
            </option>
          ))}
        </select>
        <button
          type="button"
          aria-pressed={diffMode}
          onClick={() => setDiffMode((d) => !d)}
          disabled={iterations.length < 2}
          title={iterations.length < 2 ? "Need two iterations to diff" : "Compare two iterations"}
          className={cn(
            "rounded-md border border-gray-300 px-2 py-1.5 text-xs dark:border-gray-700",
            diffMode ? "bg-blue-100 dark:bg-blue-900" : "hover:bg-gray-100 dark:hover:bg-gray-800",
            iterations.length < 2 && "opacity-50",
          )}
        >
          {diffMode ? "Hide diff" : "Diff iterations"}
        </button>
        {diffMode && (
          <>
            <label className="text-xs text-gray-600 dark:text-gray-400" htmlFor={`diff-select-${claimId}`}>
              Compare with
            </label>
            <select
              id={`diff-select-${claimId}`}
              value={compareIteration ?? ""}
              onChange={(e) => setCompareIteration(Number(e.target.value))}
              className="h-9 rounded-md border border-gray-300 bg-white px-2 text-sm dark:border-gray-700 dark:bg-gray-900"
            >
              {iterations
                .filter((it) => it.iteration !== iteration)
                .map((it) => (
                  <option key={it.iteration} value={it.iteration}>
                    Iteration {it.iteration}
                  </option>
                ))}
            </select>
          </>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-[220px_1fr]">
        <div
          ref={treeRef}
          role="tree"
          aria-label={`Files in iteration ${iteration}`}
          className="flex max-h-72 flex-col gap-1 overflow-auto rounded-lg border border-gray-200 p-2 dark:border-gray-800"
          onKeyDown={onTreeKeyDown}
        >
          {files.length === 0 ? (
            <p className="px-2 py-1 text-xs text-gray-600 dark:text-gray-400">
              This iteration saved no files.
            </p>
          ) : (
            files.map((f, idx) => {
              const selected = idx === fileIndex;
              const isNew = newFiles?.has(fileKey(claimId, iteration ?? 0, f.index)) ?? false;
              return (
                <button
                  key={f.index}
                  type="button"
                  role="treeitem"
                  aria-selected={selected}
                  aria-label={`${f.name}, ${f.size} bytes`}
                  tabIndex={selected ? 0 : -1}
                  onClick={() => {
                    setFileIndex(idx);
                    setHighlightLine(null);
                  }}
                  className={cn(
                    "flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left font-mono text-xs",
                    selected
                      ? "bg-blue-100 dark:bg-blue-900"
                      : "hover:bg-gray-100 dark:hover:bg-gray-800",
                  )}
                >
                  <span className="truncate">{f.name}</span>
                  <span className="flex shrink-0 items-center gap-1 text-gray-500">
                    {isNew && (
                      <span className="rounded-full bg-green-100 px-1.5 text-[10px] font-semibold text-green-800 ring-1 ring-inset ring-green-600/20 dark:bg-green-900/40 dark:text-green-200">
                        new
                      </span>
                    )}
                    <span>{(f.size / 1024).toFixed(1)}k</span>
                  </span>
                </button>
              );
            })
          )}
        </div>

        <div className="min-w-0">
          {fileQuery.isLoading ? (
            <LoadingState label="Loading file…" />
          ) : fileQuery.isError ? (
            <ErrorState
              title="Could not load this file."
              message="The backend did not answer or the file is not ready."
              onRetry={() => void fileQuery.refetch()}
            />
          ) : fileQuery.data && selectedFile ? (
            diffMode ? (
              <DiffView
                fileName={selectedFile.name}
                compareIteration={compareIteration}
                compareMissing={compareFileIndex < 0}
                compareLoading={compareQuery.isLoading}
                compareError={compareQuery.isError}
                rows={diffRows}
                onRetryCompare={() => void compareQuery.refetch()}
              />
            ) : (
              <CodeViewer
                fileName={selectedFile.name}
                code={fileQuery.data.text}
                truncated={fileQuery.data.truncated}
                binary={fileQuery.data.binary}
                highlightLine={highlightLine}
                anchorPrefix={anchorPrefix}
              />
            )
          ) : null}
        </div>
      </div>
    </div>
  );
}

function DiffView({
  fileName,
  compareIteration,
  compareMissing,
  compareLoading,
  compareError,
  rows,
  onRetryCompare,
}: {
  fileName: string;
  compareIteration: number | null;
  compareMissing: boolean;
  compareLoading: boolean;
  compareError: boolean;
  rows: ReturnType<typeof diffLines> | null;
  onRetryCompare: () => void;
}) {
  if (compareMissing) {
    return (
      <EmptyState
        title="File not in the other iteration."
        hint={`"${fileName}" does not exist in iteration ${compareIteration}. Pick a file present in both iterations.`}
      />
    );
  }
  if (compareLoading) return <LoadingState label="Loading comparison…" />;
  if (compareError) {
    return (
      <ErrorState
        title="Could not load the comparison file."
        message="The backend did not answer."
        onRetry={onRetryCompare}
      />
    );
  }
  if (!rows) return <LoadingState label="Computing diff…" />;
  if (rows.length === 0) {
    return <EmptyState title="No differences." hint="The two iterations are identical for this file." />;
  }
  return (
    <div className="flex flex-col gap-2" aria-label={`Diff for ${fileName}`}>
      <p className="text-xs text-gray-600 dark:text-gray-400">
        Comparing iteration {compareIteration} → current. Added lines are marked
        with + and removed lines with −.
      </p>
      <pre className="overflow-auto rounded-lg border border-gray-200 bg-white text-xs dark:border-gray-800 dark:bg-gray-950">
        <code className="block min-w-max">
          {rows.map((row, i) => (
            <span
              key={i}
              className={cn(
                "flex px-0",
                row.type === "add" && "bg-green-50 dark:bg-green-950/50",
                row.type === "del" && "bg-red-50 dark:bg-red-950/50",
              )}
            >
              <span className="w-8 shrink-0 select-none px-1 py-px text-right font-mono text-gray-400">
                {row.type === "add" ? "+" : row.type === "del" ? "−" : " "}
              </span>
              <span className="w-12 shrink-0 select-none px-1 py-px text-right font-mono text-gray-400">
                {row.type === "add" ? row.newLineNo : row.oldLineNo}
              </span>
              <span className="flex-1 whitespace-pre px-2 py-px font-mono">{row.text}</span>
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}
