import { useEffect, useState } from "react";

// Backend verdicts are displayed only. This page never computes or
// changes a verdict (see AGENTS.md hard rules).
export default function App() {
  const [health, setHealth] = useState<string>("checking…");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json() as Promise<{ status: string }>;
      })
      .then((data) => {
        if (!cancelled) {
          setHealth(data.status);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setHealth(`unreachable (${err instanceof Error ? err.message : "error"})`);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-2xl font-semibold">ClaimLens</h1>
      <p className="mt-2 text-sm text-gray-600">
        Backend status: <span data-testid="health">{health}</span>
      </p>
    </main>
  );
}
