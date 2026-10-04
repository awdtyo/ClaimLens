/**
 * SSE event helpers. The backend replays `events.jsonl` from the start
 * on every (re)connection, so the client must merge without duplicating
 * log lines. Events carry no id, so the dedupe key is built from the
 * event payload. Pure functions live here so they are unit-testable;
 * the `useRunEvents` hook wires them to an EventSource.
 */

export interface RunEvent {
  ts?: string;
  run_id?: string;
  stage: string;
  status: string;
  message?: string | null;
  data?: unknown;
}

export function eventKey(event: RunEvent): string {
  return [event.ts ?? "", event.stage, event.status, event.message ?? ""].join(
    "|",
  );
}

/**
 * Merge incoming events into the existing list, skipping events whose
 * key was already seen. Order is preserved: existing first, then new.
 */
export function mergeEvents(
  existing: RunEvent[],
  incoming: RunEvent[],
): RunEvent[] {
  const seen = new Set(existing.map(eventKey));
  const merged = [...existing];
  for (const event of incoming) {
    const key = eventKey(event);
    if (!seen.has(key)) {
      seen.add(key);
      merged.push(event);
    }
  }
  return merged;
}

/** Parse one SSE `data:` line; returns null for blank/heartbeat lines. */
export function parseEventLine(line: string): RunEvent | null {
  const trimmed = line.trim();
  if (!trimmed) return null;
  const payload = trimmed.startsWith("data:")
    ? trimmed.slice("data:".length).trim()
    : trimmed;
  if (!payload || payload === "[DONE]") return null;
  try {
    const parsed = JSON.parse(payload) as RunEvent;
    if (!parsed || typeof parsed.stage !== "string") return null;
    return parsed;
  } catch {
    return null;
  }
}
