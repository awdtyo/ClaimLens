import { verdictMeta } from "../lib/verdict";
import { cn } from "../lib/utils";

/**
 * Verdict badge: icon + text label + color. Color is never the only
 * signal. The status string comes from the backend and is shown as-is.
 */
export default function VerdictBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const meta = verdictMeta(status);
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        meta.badgeClass,
        className,
      )}
    >
      <Icon size={14} aria-hidden="true" />
      <span>{meta.label}</span>
    </span>
  );
}
