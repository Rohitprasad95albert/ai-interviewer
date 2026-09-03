/**
 * Thin fetch wrapper around the FastAPI backend.
 *
 * NEXT_PUBLIC_API_URL is inlined into the browser bundle at build time (see
 * Next.js env var docs), so it's safe to reference on the client - it must
 * never hold a secret, only the backend's public base URL.
 *
 * Field names intentionally mirror the backend's Pydantic schemas
 * (snake_case) exactly, rather than converting to camelCase, so the shape
 * on the wire and the shape in the frontend never silently drift apart.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: "ok" | "degraded";
  environment: string;
  database: "connected" | "unavailable";
};

export type Topic = "dsa" | "oop" | "dbms" | "os" | "cn";
export type Difficulty = "easy" | "medium" | "hard";
export type InterviewStatus =
  | "setup"
  | "questioning"
  | "listening"
  | "evaluating"
  | "follow_up"
  | "next_question"
  | "completed"
  | "cancelled";

export type QuestionOut = {
  id: string;
  index: number;
  topic: Topic;
  difficulty: Difficulty;
  question_text: string;
  concepts: string[];
  is_follow_up: boolean;
};

export type AnswerEvaluation = {
  technical_accuracy: number;
  depth: number;
  completeness: number;
  clarity: number;
  relevance: number;
  communication: number;
  overall: number;
  strengths: string[];
  weaknesses: string[];
  missing_concepts: string[];
  follow_up_recommended: boolean;
  follow_up_reason: string;
  suggested_next_difficulty: Difficulty;
};

export type EvaluationOut = {
  scores: AnswerEvaluation;
  vague_flags: string[];
};

export type InterviewOut = {
  id: string;
  status: InterviewStatus;
  topics: Topic[];
  difficulty: Difficulty;
  current_difficulty: Difficulty;
  question_count: number;
  current_question_index: number;
  current_question: QuestionOut | null;
  created_at: string;
  completed_at: string | null;
};

export type SubmitAnswerResponse = {
  evaluation: EvaluationOut;
  interview: InterviewOut;
};

export type InterviewReport = {
  interview: InterviewOut;
  questions: QuestionOut[];
  evaluations: EvaluationOut[];
  average_overall: number;
};

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // response wasn't JSON - keep the generic message
    }
    throw new ApiError(detail, response.status);
  }

  return response.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export async function createInterview(params: {
  topics: Topic[];
  difficulty: Difficulty;
  question_count: number;
}): Promise<InterviewOut> {
  return request<InterviewOut>("/api/interviews", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function getInterview(id: string): Promise<InterviewOut> {
  return request<InterviewOut>(`/api/interviews/${id}`);
}

export async function submitAnswer(
  id: string,
  answerText: string,
): Promise<SubmitAnswerResponse> {
  return request<SubmitAnswerResponse>(`/api/interviews/${id}/answer`, {
    method: "POST",
    body: JSON.stringify({ answer_text: answerText }),
  });
}

export async function getReport(id: string): Promise<InterviewReport> {
  return request<InterviewReport>(`/api/interviews/${id}/report`);
}

export { ApiError, API_BASE_URL };
