import type { Assumption, AssumptionEffect } from "../api/models";
import type { ClaimRow } from "../lib/claims";
import { formatValue } from "../lib/format";
import { Button, Chip } from "./ui";
import VerdictBadge from "./VerdictBadge";

interface ClaimDetailProps {
  row: ClaimRow;
  assumptions: Assumption[];
  onViewLogs: () => void;
}

function confidenceClass(level: string): string {
  switch (level) {
    case "high":
      return "bg-green-100 text-green-800 ring-green-600/20 dark:bg-green-900/40 dark:text-green-200";
    case "medium":
      return "bg-amber-100 text-amber-800 ring-amber-600/20 dark:bg-amber-900/40 dark:text-amber-200";
    default:
      return "bg-gray-100 text-gray-700 ring-gray-500/20 dark:bg-gray-800 dark:text-gray-300";
  }
}

/** Assumptions ordered by largest absolute sensitivity effect first. */
export function rankAssumptions(
  assumptions: Assumption[],
  effects: AssumptionEffect[],
): { assumption: Assumption; effects: AssumptionEffect[]; maxDelta: number }[] {
  return assumptions
    .map((assumption) => {
      const related = effects.filter((e) => e.assumption_id === assumption.id);
      const maxDelta = related.reduce(
        (m, e) => Math.max(m, Math.abs(e.delta ?? 0)),
        0,
      );
      return { assumption, effects: related, maxDelta };
    })
    .sort((a, b) => {
      if (b.effects.length !== a.effects.length) {
        return b.effects.length - a.effects.length;
      }
      return b.maxDelta - a.maxDelta;
    });
}

function SensitivityChart({
  effects,
  mainMeasured,
}: {
  effects: AssumptionEffect[];
  mainMeasured: number | null;
}) {
  if (effects.length === 0 || mainMeasured === null) return null;
  const values = [mainMeasured, ...effects.map((e) => e.measured_value ?? 0)];
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  return (
    <figure aria-label="Sensitivity chart" className="flex flex-col gap-2">
      <figcaption className="text-sm font-medium">
        Sensitivity: measured value when one assumption is varied
      </figcaption>
      <div role="img" aria-label={`Main measurement ${mainMeasured}. ${effects.map((e) => `${e.alt_value}: ${e.measured_value}`).join(". ")}`}>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-36 shrink-0 truncate text-gray-600 dark:text-gray-400">
              Main measurement
            </span>
            <div className="h-4 flex-1 rounded bg-gray-100 dark:bg-gray-800">
              <div
                className="h-4 rounded bg-blue-600 dark:bg-blue-400"
                style={{ width: `${((mainMeasured - min) / span) * 80 + 20}%` }}
              />
            </div>
            <span className="w-16 shrink-0 text-right font-mono">{mainMeasured}</span>
          </div>
          {effects.map((effect, i) => (
            <div key={`${effect.assumption_id}-${i}`} className="flex items-center gap-2 text-xs">
              <span className="w-36 shrink-0 truncate text-gray-600 dark:text-gray-400" title={effect.alt_value}>
                {effect.alt_value}
              </span>
              <div className="h-4 flex-1 rounded bg-gray-100 dark:bg-gray-800">
                <div
                  className="h-4 rounded bg-amber-500 dark:bg-amber-400"
                  style={{
                    width: `${(((effect.measured_value ?? 0) - min) / span) * 80 + 20}%`,
                  }}
                />
              </div>
              <span className="w-16 shrink-0 text-right font-mono">
                {formatValue(effect.measured_value)}
                {effect.delta != null && (
                  <span className="text-gray-500"> ({effect.delta > 0 ? "+" : ""}{effect.delta})</span>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>
    </figure>
  );
}

/**
 * Claim detail panel. All verdicts, values and effects are backend
 * data shown as-is; differences are arithmetic display only and never
 * change the verdict.
 */
export default function ClaimDetail({ row, assumptions, onViewLogs }: ClaimDetailProps) {
  const { claim, verdict } = row;
  const reported = claim.reported_value ?? null;
  const measured = row.measured;
  const delta =
    reported !== null && measured !== null ? measured - reported : null;
  const scaled = Boolean(verdict?.scaled || (row.scaleFactor ?? 1) < 1);
  const ranked = verdict ? rankAssumptions(assumptions, verdict.assumption_effects) : [];

  return (
    <article aria-labelledby={`claim-${claim.id}-heading`} className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 id={`claim-${claim.id}-heading`} className="font-mono text-sm text-gray-500 dark:text-gray-400">
          {claim.id}
        </h3>
        {verdict && <VerdictBadge status={verdict.status} />}
        <span className="text-xs text-gray-600 dark:text-gray-400">{claim.source_ref}</span>
      </div>
      <p className="text-sm">{claim.text}</p>

      <div className="grid grid-cols-2 gap-3" aria-label="Reported versus measured">
        <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-800">
          <p className="text-xs text-gray-600 dark:text-gray-400">Reported (paper)</p>
          <p className="mt-1 font-mono text-lg">{formatValue(reported)}</p>
        </div>
        <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-800">
          <p className="text-xs text-gray-600 dark:text-gray-400">Measured (sandbox)</p>
          <p className="mt-1 font-mono text-lg">{formatValue(measured)}</p>
        </div>
      </div>
      {delta !== null && (
        <p className="text-xs text-gray-600 dark:text-gray-400">
          Difference: {delta > 0 ? "+" : ""}{delta} (shown for context; the
          verdict above was computed by the backend).
        </p>
      )}

      {scaled && (
        <div
          role="note"
          aria-label="Scale limitations"
          className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
        >
          <p className="font-medium">Scaled run: interpret with care.</p>
          <p className="mt-1">
            This experiment ran at {row.scaleFactor ? `${row.scaleFactor * 100}%` : "reduced"} scale.
            A scaled run cannot fully confirm or refute the paper: the
            strongest negative outcome it allows is “partially replicated”
            or “untestable at this scale”.
          </p>
        </div>
      )}

      {verdict && (
        <div className="flex flex-col gap-1">
          <h4 className="text-sm font-medium">Why this verdict</h4>
          <p className="text-sm text-gray-700 dark:text-gray-300">{verdict.rationale}</p>
        </div>
      )}

      {ranked.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-sm font-medium">Assumptions, ranked by effect</h4>
          <ul className="flex flex-col gap-2">
            {ranked.map(({ assumption, effects, maxDelta }) => (
              <li
                key={assumption.id}
                className="rounded-lg border border-gray-200 p-3 dark:border-gray-800"
              >
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-medium">{assumption.detail}</span>
                  <Chip className={confidenceClass(assumption.confidence)}>
                    {assumption.confidence} confidence
                  </Chip>
                  {effects.length > 0 && (
                    <Chip aria-label={`Largest measured change ${maxDelta}`}>
                      max change {maxDelta}
                    </Chip>
                  )}
                </div>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  Chose: {assumption.value_chosen}. {assumption.reason}
                </p>
                {effects.length > 0 && (
                  <ul className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    {effects.map((e, i) => (
                      <li key={`${e.assumption_id}-${i}`}>
                        {e.alt_value} → measured {formatValue(e.measured_value)}
                        {e.delta != null && ` (change ${e.delta > 0 ? "+" : ""}${e.delta})`}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {verdict && verdict.assumption_effects.length > 0 && (
        <SensitivityChart effects={verdict.assumption_effects} mainMeasured={measured} />
      )}

      {row.primaryEvidence && (
        <div className="flex flex-col gap-1 text-sm">
          <h4 className="font-medium">Evidence</h4>
          <p className="text-gray-600 dark:text-gray-400">{row.primaryEvidence.method}</p>
          {row.primaryEvidence.logs_ref && (
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Log: <code>{row.primaryEvidence.logs_ref}</code>{" "}
              <Button variant="ghost" size="sm" onClick={onViewLogs}>
                View in run log
              </Button>
            </p>
          )}
        </div>
      )}
    </article>
  );
}
