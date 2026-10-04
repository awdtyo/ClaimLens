import { Check, Loader2, X } from "lucide-react";
import { getStageList, stageLabel, type RunDetail } from "../api/client";
import { elapsedSeconds, formatDuration } from "../lib/format";
import { cn } from "../lib/utils";

function stageStatus(run: RunDetail, stage: string): string {
  return run.stages?.[stage]?.status ?? "queued";
}

function StageIcon({ status }: { status: string }) {
  if (status === "done") {
    return <Check size={16} aria-hidden="true" className="text-green-700 dark:text-green-300" />;
  }
  if (status === "failed") {
    return <X size={16} aria-hidden="true" className="text-red-700 dark:text-red-300" />;
  }
  if (status === "running") {
    return <Loader2 size={16} aria-hidden="true" className="animate-spin text-blue-700 dark:text-blue-300" />;
  }
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 rounded-full bg-gray-300 dark:bg-gray-700"
    />
  );
}

/**
 * Pipeline stepper driven by the stage list in the API run state.
 * Shows per-stage status, elapsed time and errors. Unknown future
 * stages render with a generic label instead of breaking.
 */
export default function PipelineStepper({ run }: { run: RunDetail }) {
  const stages = getStageList(run);
  return (
    <ol aria-label="Pipeline stages" className="flex flex-col gap-1">
      {stages.map((stage, index) => {
        const state = run.stages?.[stage];
        const status = stageStatus(run, stage);
        const elapsed = elapsedSeconds(state?.started_at, state?.ended_at);
        const failed = status === "failed";
        return (
          <li
            key={stage}
            aria-current={status === "running" ? "step" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2",
              failed && "bg-red-50 ring-1 ring-inset ring-red-300 dark:bg-red-950 dark:ring-red-800",
              status === "running" && "bg-blue-50 dark:bg-blue-950",
            )}
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-gray-300 dark:border-gray-700">
              <StageIcon status={status} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className="text-sm font-medium capitalize">
                  {index + 1}. {stageLabel(stage)}
                </span>
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  {status}
                  {elapsed !== null && ` · ${formatDuration(elapsed)}`}
                </span>
              </div>
              {failed && state?.error && (
                <p role="alert" className="mt-0.5 text-xs text-red-700 dark:text-red-300">
                  {state.error}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
