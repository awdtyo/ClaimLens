import { useQuery } from "@tanstack/react-query";
import { fetchCodeFile, fetchCodeTree } from "../api/code";

/** File tree of generated code for a run (server-enumerated). */
export function useCodeTree(runId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["code-tree", runId],
    queryFn: () => fetchCodeTree(runId as string),
    enabled: Boolean(runId) && enabled,
  });
}

/** One code file by server-assigned index; cached per file. */
export function useCodeFile(
  runId: string | undefined,
  claimId: string,
  iteration: number | null,
  fileIndex: number | null,
  enabled = true,
) {
  return useQuery({
    queryKey: ["code-file", runId, claimId, iteration, fileIndex],
    queryFn: () =>
      fetchCodeFile(runId as string, claimId, iteration as number, fileIndex as number),
    enabled:
      Boolean(runId) && iteration !== null && fileIndex !== null && enabled,
    staleTime: Infinity,
  });
}
