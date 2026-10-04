/** Format an ISO timestamp for display; returns a fallback on bad input. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** Format a measured/reported number; null means the paper gave no number. */
export function formatValue(value: number | null | undefined): string {
  if (value === null || value === undefined) return "n/a";
  return String(value);
}

/** Format an elapsed duration in seconds as "1m 23s" or "45s". */
export function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const m = Math.floor(s / 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${s % 60}s`;
}

/** Elapsed seconds between two ISO timestamps; null when not computable. */
export function elapsedSeconds(
  startedAt: string | null | undefined,
  endedAt: string | null | undefined,
  nowMs = Date.now(),
): number | null {
  if (!startedAt) return null;
  const start = new Date(startedAt).getTime();
  if (Number.isNaN(start)) return null;
  const end = endedAt ? new Date(endedAt).getTime() : nowMs;
  if (Number.isNaN(end)) return null;
  return Math.max(0, (end - start) / 1000);
}
