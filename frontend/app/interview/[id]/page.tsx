"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ApiError,
  getInterview,
  submitAnswer,
  type EvaluationOut,
  type InterviewOut,
} from "@/lib/api";

type Phase =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "answering" }
  | { kind: "submitting" }
  | { kind: "feedback"; evaluation: EvaluationOut };

function ScoreRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-foreground/60">{label}</span>
      <span className="font-medium">{value}/10</span>
    </div>
  );
}

export default function LiveInterviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const interviewId = params.id;

  const [interview, setInterview] = useState<InterviewOut | null>(null);
  const [answerText, setAnswerText] = useState("");
  const [phase, setPhase] = useState<Phase>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    getInterview(interviewId)
      .then((data) => {
        if (cancelled) return;
        if (data.status === "completed") {
          router.replace(`/interview/${interviewId}/report`);
          return;
        }
        setInterview(data);
        setPhase({ kind: "answering" });
      })
      .catch((err) => {
        if (cancelled) return;
        setPhase({
          kind: "error",
          message: err instanceof ApiError ? err.message : "Could not load this interview.",
        });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewId]);

  async function handleSubmit() {
    if (!answerText.trim()) return;
    setPhase({ kind: "submitting" });
    try {
      const result = await submitAnswer(interviewId, answerText);
      setInterview(result.interview);
      setAnswerText("");
      setPhase({ kind: "feedback", evaluation: result.evaluation });
    } catch (err) {
      setPhase({
        kind: "error",
        message: err instanceof ApiError ? err.message : "Could not submit that answer.",
      });
    }
  }

  function handleContinue() {
    if (interview?.status === "completed") {
      router.push(`/interview/${interviewId}/report`);
    } else {
      setPhase({ kind: "answering" });
    }
  }

  if (phase.kind === "loading") {
    return <CenteredMessage>Loading interview…</CenteredMessage>;
  }

  if (phase.kind === "error") {
    return <CenteredMessage tone="error">{phase.message}</CenteredMessage>;
  }

  if (!interview) return null;

  return (
    <main className="mx-auto flex min-h-full max-w-2xl flex-col px-6 py-12">
      <header className="mb-8 flex items-center justify-between text-sm text-foreground/60">
        <span>AI Interviewer</span>
        <span>
          Question {Math.min(interview.current_question_index + 1, interview.question_count)} of{" "}
          {interview.question_count}
        </span>
      </header>

      {phase.kind === "feedback" ? (
        <FeedbackView
          evaluation={phase.evaluation}
          completed={interview.status === "completed"}
          onContinue={handleContinue}
        />
      ) : (
        <QuestionView
          questionText={interview.current_question?.question_text ?? ""}
          topic={interview.current_question?.topic ?? ""}
          answerText={answerText}
          onAnswerChange={setAnswerText}
          onSubmit={handleSubmit}
          submitting={phase.kind === "submitting"}
        />
      )}
    </main>
  );
}

function QuestionView({
  questionText,
  topic,
  answerText,
  onAnswerChange,
  onSubmit,
  submitting,
}: {
  questionText: string;
  topic: string;
  answerText: string;
  onAnswerChange: (value: string) => void;
  onSubmit: () => void;
  submitting: boolean;
}) {
  return (
    <div className="flex flex-1 flex-col">
      <span className="mb-2 inline-block w-fit rounded-full bg-foreground/10 px-2.5 py-1 text-xs font-medium uppercase tracking-wide text-foreground/60">
        {topic}
      </span>
      <p className="text-lg leading-relaxed">{questionText}</p>

      <textarea
        value={answerText}
        onChange={(e) => onAnswerChange(e.target.value)}
        placeholder="Type your answer…"
        rows={8}
        className="mt-6 flex-1 resize-none rounded-lg border border-foreground/10 p-4 text-sm outline-none focus:border-foreground/30"
        disabled={submitting}
      />

      <button
        type="button"
        onClick={onSubmit}
        disabled={submitting || !answerText.trim()}
        className="mt-4 self-end rounded-lg bg-foreground px-5 py-2.5 text-sm font-medium text-background disabled:opacity-50"
      >
        {submitting ? "Evaluating…" : "Submit Answer"}
      </button>
    </div>
  );
}

function FeedbackView({
  evaluation,
  completed,
  onContinue,
}: {
  evaluation: EvaluationOut;
  completed: boolean;
  onContinue: () => void;
}) {
  const { scores, vague_flags } = evaluation;
  return (
    <div className="flex flex-1 flex-col">
      <div className="rounded-xl border border-foreground/10 p-6">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-medium text-foreground/60">Evaluation</h2>
          <span className="text-2xl font-semibold">{scores.overall.toFixed(1)}/10</span>
        </div>

        <div className="mt-4 space-y-1.5">
          <ScoreRow label="Technical accuracy" value={scores.technical_accuracy} />
          <ScoreRow label="Depth" value={scores.depth} />
          <ScoreRow label="Completeness" value={scores.completeness} />
          <ScoreRow label="Clarity" value={scores.clarity} />
          <ScoreRow label="Communication" value={scores.communication} />
        </div>

        {vague_flags.length > 0 && (
          <div className="mt-4 rounded-lg bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
            {vague_flags.map((flag, i) => (
              <p key={i}>{flag}</p>
            ))}
          </div>
        )}

        {scores.weaknesses.length > 0 && (
          <div className="mt-4 text-sm">
            <p className="font-medium text-foreground/60">To improve:</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5">
              {scores.weaknesses.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={onContinue}
        className="mt-6 self-end rounded-lg bg-foreground px-5 py-2.5 text-sm font-medium text-background"
      >
        {completed ? "View full report" : "Next question"}
      </button>
    </div>
  );
}

function CenteredMessage({
  children,
  tone = "default",
}: {
  children: React.ReactNode;
  tone?: "default" | "error";
}) {
  return (
    <main className="flex min-h-full items-center justify-center px-6">
      <p className={`text-sm ${tone === "error" ? "text-red-600 dark:text-red-400" : "text-foreground/60"}`}>
        {children}
      </p>
    </main>
  );
}
