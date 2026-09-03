"""
Pydantic schemas for the interview API - request/response shapes and the
structured shape we require the LLM to return (validated, never trusted
blindly - see AnswerEvaluation / GeneratedQuestion below).
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

Difficulty = Literal["easy", "medium", "hard"]

# Only technical topics are wired up in Milestone 2. HR/project/resume modes
# come in later milestones - this is intentionally narrow for now.
Topic = Literal["dsa", "oop", "dbms", "os", "cn"]


class InterviewState(StrEnum):
    """
    Server-authoritative interview state machine (spec section 20).

    Milestone 2 only drives SETUP -> QUESTIONING -> EVALUATING ->
    NEXT_QUESTION -> COMPLETED. LISTENING and FOLLOW_UP exist as states
    because the spec defines them for the voice layer and the adaptive
    follow-up logic (Milestones 5 and 8) - keeping them in the enum now
    avoids a breaking schema change later, but nothing transitions into
    them yet.
    """

    SETUP = "setup"
    QUESTIONING = "questioning"
    LISTENING = "listening"
    EVALUATING = "evaluating"
    FOLLOW_UP = "follow_up"
    NEXT_QUESTION = "next_question"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# --- Requests ----------------------------------------------------------


class CreateInterviewRequest(BaseModel):
    topics: list[Topic] = Field(min_length=1)
    difficulty: Difficulty = "medium"
    question_count: int = Field(default=5, ge=1, le=20)


class SubmitAnswerRequest(BaseModel):
    answer_text: str = Field(min_length=1, max_length=8000)


# --- LLM-facing structured output (validated on the way in) ------------


class GeneratedQuestion(BaseModel):
    """What we require the question-generator LLM call to return."""

    question: str
    topic: Topic
    difficulty: Difficulty
    concepts: list[str] = Field(default_factory=list)


class AnswerEvaluation(BaseModel):
    """
    What we require the evaluator LLM call to return (spec section 11/24).

    Scores are 0-10 ints per criterion; `overall` is a float average. These
    are the model's structured self-report, not an objective measurement -
    the UI should present them accordingly (see spec section 11).
    """

    technical_accuracy: int = Field(ge=0, le=10)
    depth: int = Field(ge=0, le=10)
    completeness: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    relevance: int = Field(ge=0, le=10)
    communication: int = Field(ge=0, le=10)
    overall: float = Field(ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)
    follow_up_recommended: bool = False
    follow_up_reason: str = ""
    suggested_next_difficulty: Difficulty = "medium"


# --- Responses -----------------------------------------------------------


class QuestionOut(BaseModel):
    id: str
    index: int
    topic: Topic
    difficulty: Difficulty
    question_text: str
    concepts: list[str]
    is_follow_up: bool = False


class EvaluationOut(BaseModel):
    scores: AnswerEvaluation
    vague_flags: list[str]


class InterviewOut(BaseModel):
    id: str
    status: InterviewState
    topics: list[Topic]
    difficulty: Difficulty  # base/target difficulty chosen at setup - fixed for the session
    current_difficulty: Difficulty  # live, adapted difficulty (spec section 8) - moves as the interview progresses
    question_count: int
    current_question_index: int
    current_question: QuestionOut | None = None
    created_at: datetime
    completed_at: datetime | None = None


class SubmitAnswerResponse(BaseModel):
    evaluation: EvaluationOut
    interview: InterviewOut


class InterviewReport(BaseModel):
    """Final summary once an interview reaches COMPLETED."""

    interview: InterviewOut
    questions: list[QuestionOut]
    evaluations: list[EvaluationOut]
    average_overall: float
