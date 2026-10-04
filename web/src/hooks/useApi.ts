import { useQuery } from "@tanstack/react-query";
import {
  fetchArtifact,
  fetchReport,
  fetchRun,
  fetchRuns,
} from "../api/client";

/** Polling interval (ms) for run detail while a run is active. */
const ACTIVE_POLL_MS = 2000;

export function useRuns() {
  return useQuery({
    queryKey: ["runs"],
    queryFn: () => fetchRuns(),
  });
}

export function useDemoRuns() {
  return useQuery({
    queryKey: ["runs", { demo: true }],
    queryFn: () => fetchRuns(true),
  });
}

export function useRun(runId: string | undefined) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () => fetchRun(runId as string),
    enabled: Boolean(runId),
    // Poll while the run is active; stop on terminal statuses.
    refetchInterval: (query) => {
      const status = (query.state.data as { status?: string } | undefined)?.status;
      return status && ["done", "failed", "cancelled"].includes(status)
        ? false
        : ACTIVE_POLL_MS;
    },
  });
}

export function useArtifact<T>(
  runId: string | undefined,
  name: string,
  parse: (data: unknown) => T | null,
  enabled = true,
) {
  return useQuery({
    queryKey: ["artifact", runId, name],
    queryFn: async () => {
      const data = await fetchArtifact(runId as string, name);
      const parsed = parse(data);
      if (parsed === null) {
        throw new Error(`Artifact "${name}" has an unexpected shape.`);
      }
      return parsed;
    },
    enabled: Boolean(runId) && enabled,
  });
}

export function useReportText(runId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["artifact", runId, "report"],
    queryFn: () => fetchReport(runId as string),
    enabled: Boolean(runId) && enabled,
  });
}
