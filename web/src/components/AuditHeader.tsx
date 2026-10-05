import { Link } from "react-router-dom";
import { artifactUrl } from "../api/client";
import type { RunDetail } from "../api/client";
import { Chip } from "./ui";

/**
 * Compact audit header (72–96px): back link, paper identity with real
 * metadata badges, and run status with paper/export actions.
 */
export default function AuditHeader({
  runId,
  run,
  title,
  badges,
}: {
  runId: string;
  run: RunDetail;
  title: string;
  badges: string[];
}) {
  const complete = run.status === "done";
  return (
    <div className="flex flex-col gap-2">
      <Link to="/" className="cl-meta w-fit underline underline-offset-4">
        ← Back to Audits
      </Link>
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <p className="cl-meta font-medium uppercase tracking-[0.12em]">Paper title</p>
          <h1 className="truncate text-xl font-semibold tracking-tight md:text-2xl">
            {title || run.filename || runId}
          </h1>
          {badges.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1.5" aria-label="Paper topics">
              {badges.slice(0, 5).map((b) => (
                <Chip key={b}>{b}</Chip>
              ))}
            </div>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span
            role="status"
            className="inline-flex items-center gap-1.5 text-xs font-medium"
          >
            <span
              aria-hidden="true"
              className={
                complete
                  ? "inline-block h-2 w-2 rounded-full bg-[var(--ok)]"
                  : "inline-block h-2 w-2 rounded-full bg-[var(--warn)]"
              }
            />
            {complete ? "AUDIT COMPLETE" : `AUDIT ${run.status.toUpperCase()}`}
          </span>
          <a href={artifactUrl(runId, "paper")} target="_blank" rel="noreferrer" className="cl-btn cl-btn-outline cl-btn-sm">
            View Paper
          </a>
          <a href={artifactUrl(runId, "report")} download className="cl-btn cl-btn-primary cl-btn-sm">
            Export
          </a>
        </div>
      </div>
    </div>
  );
}
