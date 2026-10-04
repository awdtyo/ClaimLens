import { useEffect, useRef, useState } from "react";
import { eventKey, mergeEvents, parseEventLine, type RunEvent } from "../lib/events";

export interface RunEventsState {
  events: RunEvent[];
  connected: boolean;
  /** Number of reconnect attempts so far. */
  retries: number;
  /** True once the backend sent the terminal run event. */
  complete: boolean;
}

const MAX_BACKOFF_MS = 10000;

function isTerminal(event: RunEvent): boolean {
  return event.stage === "run" && (event.status === "done" || event.status === "failed");
}

/**
 * Subscribe to the SSE event stream for a run.
 *
 * The backend replays stored events from the start on every connection,
 * so reconnects merge with dedupe (`mergeEvents`) and never duplicate
 * log lines. Reconnect uses exponential backoff up to 10 s.
 */
export function useRunEvents(runId: string | undefined): RunEventsState {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [retries, setRetries] = useState(0);
  const [complete, setComplete] = useState(false);
  const seenRef = useRef<Set<string>>(new Set());
  const doneRef = useRef(false);

  useEffect(() => {
    seenRef.current = new Set();
    doneRef.current = false;
    setEvents([]);
    setRetries(0);
    setComplete(false);
    if (!runId) return;

    let stopped = false;
    let backoff = 1000;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let source: EventSource | undefined;

    const append = (batch: RunEvent[]) => {
      if (batch.length === 0 || stopped) return;
      const fresh = batch.filter((e) => {
        const key = eventKey(e);
        if (seenRef.current.has(key)) return false;
        seenRef.current.add(key);
        return true;
      });
      if (fresh.length > 0) {
        setEvents((prev) => mergeEvents(prev, fresh));
      }
    };

    const connect = () => {
      if (stopped || doneRef.current) return;
      try {
        source = new EventSource(`/api/runs/${runId}/events`);
      } catch {
        scheduleReconnect();
        return;
      }
      source.onopen = () => {
        if (!stopped) {
          setConnected(true);
          backoff = 1000;
        }
      };
      source.onmessage = (msg) => {
        const event = parseEventLine(msg.data);
        if (event) {
          append([event]);
          if (isTerminal(event)) {
            // The backend replays from the start on every connection and
            // closes after the terminal event: stop instead of looping.
            doneRef.current = true;
            source?.close();
            setConnected(false);
            setComplete(true);
          }
        }
      };
      source.onerror = () => {
        source?.close();
        if (!stopped && !doneRef.current) {
          setConnected(false);
          scheduleReconnect();
        }
      };
    };

    const scheduleReconnect = () => {
      if (stopped) return;
      setRetries((r) => r + 1);
      timer = setTimeout(() => {
        backoff = Math.min(backoff * 2, MAX_BACKOFF_MS);
        connect();
      }, backoff);
    };

    connect();
    return () => {
      stopped = true;
      source?.close();
      if (timer) clearTimeout(timer);
    };
  }, [runId]);

  return { events, connected, retries, complete };
}
