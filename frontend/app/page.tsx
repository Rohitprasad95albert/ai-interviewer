"use client";

import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "@/lib/api";

type LoadState =
  | { kind: "loading" }
  | { kind: "success"; data: HealthResponse }
  | { kind: "error"; message: string };

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${
        ok ? "bg-emerald-500" : "bg-red-500"
      }`}
      aria-hidden
    />
  );
}

export default function DashboardPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((data) => {
        if (!cancelled) setState({ kind: "success", data });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message:
              err instanceof Error
                ? err.message
                : "Could not reach the backend.",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="flex min-h-full flex-1 items-center justify-center px-6 py-16">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">
            AI Interviewer
          </h1>
          <p className="mt-1 text-sm text-foreground/60">
            Your personal, adaptive interview coach.
          </p>
        </div>

        <div className="rounded-xl border border-foreground/10 p-6">
          <h2 className="text-sm font-medium text-foreground/60">
            System status
          </h2>

          {state.kind === "loading" && (
            <div className="mt-3 flex items-center gap-2 text-sm text-foreground/60">
              <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-foreground/30" />
              Checking backend connection…
            </div>
          )}

          {state.kind === "success" && (
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <dt className="text-foreground/60">API</dt>
                <dd className="flex items-center gap-2">
                  <StatusDot ok={state.data.status === "ok"} />
                  {state.data.status}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-foreground/60">Database</dt>
                <dd className="flex items-center gap-2">
                  <StatusDot ok={state.data.database === "connected"} />
                  {state.data.database}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-foreground/60">Environment</dt>
                <dd>{state.data.environment}</dd>
              </div>
            </dl>
          )}

          {state.kind === "error" && (
            <div className="mt-3 rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">
              <p className="font-medium">Can&apos;t reach the backend.</p>
              <p className="mt-1 text-red-600/80 dark:text-red-400/80">
                {state.message} Is the FastAPI server running on{" "}
                <code>:8000</code>?
              </p>
            </div>
          )}
        </div>

        <button
          type="button"
          disabled
          title="Coming in Milestone 2 — the interview engine isn't built yet"
          className="mt-4 w-full cursor-not-allowed rounded-lg bg-foreground/10 px-4 py-2.5 text-sm font-medium text-foreground/40"
        >
          Start Interview — coming soon
        </button>
      </div>
    </main>
  );
}
