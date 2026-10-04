import { useEffect, useRef, useState } from "react";
import type { RunEvent } from "../lib/events";
import { cn } from "../lib/utils";
import { Button } from "./ui";

interface LogPanelProps {
  events: RunEvent[];
  connected: boolean;
  retries: number;
  complete: boolean;
}

/**
 * Live log panel. Autoscrolls to new lines unless paused by the user.
 * A "paused" toggle and keyboard-focusable region keep it usable with
 * screen readers and keyboards.
 */
export default function LogPanel({ events, connected, retries, complete }: LogPanelProps) {
  const [paused, setPaused] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!paused) {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [events.length, paused]);

  return (
    <section aria-labelledby="log-heading" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="log-heading" className="text-sm font-semibold">
          Live log
        </h2>
        <div className="flex items-center gap-2">
          <span
            role="status"
            className={cn(
              "inline-flex items-center gap-1.5 text-xs",
              connected
                ? "text-green-700 dark:text-green-300"
                : complete
                  ? "text-gray-600 dark:text-gray-400"
                  : "text-amber-700 dark:text-amber-300",
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                "inline-block h-2 w-2 rounded-full",
                connected
                  ? "bg-green-600 dark:bg-green-400"
                  : complete
                    ? "bg-gray-400"
                    : "bg-amber-500",
              )}
            />
            {connected
              ? "connected"
              : complete
                ? "stream complete"
                : `reconnecting… (attempt ${retries})`}
          </span>
          <Button
            variant="outline"
            size="sm"
            aria-pressed={paused}
            onClick={() => setPaused((p) => !p)}
          >
            {paused ? "Resume autoscroll" : "Pause autoscroll"}
          </Button>
        </div>
      </div>
      <div
        id="run-log"
        ref={scrollRef}
        tabIndex={0}
        role="log"
        aria-live={paused ? "off" : "polite"}
        aria-label="Pipeline log"
        className="h-64 overflow-y-auto rounded-lg border border-gray-200 bg-gray-950 p-3 font-mono text-xs text-gray-100 dark:border-gray-800"
      >
        {events.length === 0 ? (
          <p className="text-gray-400">Waiting for pipeline events…</p>
        ) : (
          <ol className="flex flex-col gap-0.5">
            {events.map((event, i) => (
              <li key={`${event.ts ?? i}-${i}`} className="break-words">
                <span className="text-gray-500">
                  {event.ts ? new Date(event.ts).toLocaleTimeString() : "—"}{" "}
                </span>
                <span className="text-blue-300">[{event.stage}]</span>{" "}
                <span
                  className={cn(
                    event.status === "failed" ? "text-red-300" : "text-gray-100",
                  )}
                >
                  {event.status}
                </span>
                {event.message && <span className="text-gray-300"> — {event.message}</span>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
