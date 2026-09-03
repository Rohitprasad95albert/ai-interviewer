"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createInterview, ApiError, type Difficulty, type Topic } from "@/lib/api";

const TOPICS: { value: Topic; label: string }[] = [
  { value: "dsa", label: "DSA" },
  { value: "oop", label: "OOP" },
  { value: "dbms", label: "DBMS" },
  { value: "os", label: "Operating Systems" },
  { value: "cn", label: "Computer Networks" },
];

const DIFFICULTIES: Difficulty[] = ["easy", "medium", "hard"];

export default function NewInterviewPage() {
  const router = useRouter();
  const [selectedTopics, setSelectedTopics] = useState<Topic[]>(["dsa"]);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [questionCount, setQuestionCount] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleTopic(topic: Topic) {
    setSelectedTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic],
    );
  }

  async function handleStart() {
    if (selectedTopics.length === 0) {
      setError("Pick at least one topic.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const interview = await createInterview({
        topics: selectedTopics,
        difficulty,
        question_count: questionCount,
      });
      router.push(`/interview/${interview.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the interview.");
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-full max-w-lg flex-col justify-center px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Technical Interview</h1>
      <p className="mt-1 text-sm text-foreground/60">
        Choose your topics and difficulty. This is Milestone 2 - fixed
        question count, no adaptivity yet.
      </p>

      <fieldset className="mt-8">
        <legend className="text-sm font-medium">Topics</legend>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {TOPICS.map((topic) => (
            <label
              key={topic.value}
              className="flex cursor-pointer items-center gap-2 rounded-lg border border-foreground/10 px-3 py-2 text-sm has-checked:border-foreground/40 has-checked:bg-foreground/5"
            >
              <input
                type="checkbox"
                checked={selectedTopics.includes(topic.value)}
                onChange={() => toggleTopic(topic.value)}
                className="accent-foreground"
              />
              {topic.label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="mt-6">
        <legend className="text-sm font-medium">Difficulty</legend>
        <div className="mt-3 flex gap-2">
          {DIFFICULTIES.map((level) => (
            <button
              key={level}
              type="button"
              onClick={() => setDifficulty(level)}
              className={`flex-1 rounded-lg border px-3 py-2 text-sm capitalize ${
                difficulty === level
                  ? "border-foreground/40 bg-foreground/5 font-medium"
                  : "border-foreground/10 text-foreground/60"
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </fieldset>

      <label className="mt-6 block">
        <span className="text-sm font-medium">Number of questions</span>
        <input
          type="number"
          min={1}
          max={20}
          value={questionCount}
          onChange={(e) => setQuestionCount(Number(e.target.value))}
          className="mt-3 w-full rounded-lg border border-foreground/10 px-3 py-2 text-sm"
        />
      </label>

      {error && (
        <p className="mt-4 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={handleStart}
        disabled={submitting}
        className="mt-8 w-full rounded-lg bg-foreground px-4 py-2.5 text-sm font-medium text-background disabled:opacity-50"
      >
        {submitting ? "Starting…" : "Start Interview"}
      </button>
    </main>
  );
}
