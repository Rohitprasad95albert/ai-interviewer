"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ApiError, getReport, type InterviewReport } from "@/lib/api";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "success"; data: InterviewReport };

export default function InterviewReportPage() {
  const params = useParams<{ id: string }>();
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    getReport(params.id)
      .then((data) => {
        if (!cancelled) setState({ kind: "success", data });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message: err instanceof ApiError ? err.message : "Could not load this report.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  if (state.kind === "loading") {
    return (
      <main className="flex min-h-full items-center justify-center">
        <p className="text-sm text-foreground/60">Loading report…</p>
      </main>
    );
  }

  if (state.kind === "error") {
    return (
      <main className="flex min-h-full items-center justify-center">
        <p className="text-sm text-red-600 dark:text-red-400">{state.message}</p>
      </main>
    );
  }

  const { interview, questions, evaluations, average_overall } = state.data;

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link href="/" className="text-sm text-foreground/60 hover:underline">
        &larr; Dashboard
      </Link>

      <div className="mt-6 flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Interview Report</h1>
          <p className="mt-1 text-sm text-foreground/60 capitalize">
            {interview.topics.join(", ")} · {interview.difficulty}
          </p>
        </div>
        <span className="text-3xl font-semibold">{average_overall.toFixed(1)}/10</span>
      </div>

      <div className="mt-8 space-y-6">
        {questions.map((question, i) => {
          const evaluation = evaluations[i];
          return (
            <div key={question.id} className="rounded-xl border border-foreground/10 p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <span className="inline-block rounded-full bg-foreground/10 px-2.5 py-1 text-xs font-medium uppercase tracking-wide text-foreground/60">
                    {question.topic}
                  </span>
                  <p className="mt-2 font-medium">{question.question_text}</p>
                </div>
                {evaluation && (
                  <span className="shrink-0 text-lg font-semibold">
                    {evaluation.scores.overall.toFixed(1)}
                  </span>
                )}
              </div>

              {evaluation && evaluation.vague_flags.length > 0 && (
                <div className="mt-3 rounded-lg bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
                  {evaluation.vague_flags.map((flag, j) => (
                    <p key={j}>{flag}</p>
                  ))}
                </div>
              )}

              {evaluation && evaluation.scores.weaknesses.length > 0 && (
                <ul className="mt-3 list-inside list-disc space-y-0.5 text-sm text-foreground/70">
                  {evaluation.scores.weaknesses.map((w, j) => (
                    <li key={j}>{w}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      <Link
        href="/interview/new"
        className="mt-8 inline-block rounded-lg bg-foreground px-5 py-2.5 text-sm font-medium text-background"
      >
        Start another interview
      </Link>
    </main>
  );
}
