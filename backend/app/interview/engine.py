"""
InterviewEngine - the deterministic orchestrator described in spec section
23: it owns every state transition and all persistence; the LLMClient is
only ever asked "what question?" or "how good is this answer?" and never
gets to decide what happens next. That decision-making stays here, in plain
Python, so it's testable without an LLM (see tests/test_interview_flow.py).
"""

import logging

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai.base import LLMClient
from app.interview import repository as repo
from app.interview.state_machine import transition
from app.interview.vague_detector import detect_vague_flags
from app.schemas.interview import (
    AnswerEvaluation,
    CreateInterviewRequest,
    EvaluationOut,
    InterviewOut,
    InterviewReport,
    InterviewState,
    QuestionOut,
    SubmitAnswerResponse,
)

logger = logging.getLogger(__name__)

# Single-user for now (spec section 2: "initially there is one primary
# user - me"). Auth and per-user scoping are Milestone 9; the user_id field
# already exists on every interview so that migration doesn't require a
# schema change later.
DEFAULT_USER_ID = "default-user"


class InterviewNotFoundError(Exception):
    pass


class InterviewNotActiveError(Exception):
    pass


def parse_object_id(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except InvalidId as exc:
        raise InterviewNotFoundError(raw_id) from exc


def _topic_for_index(topics: list[str], index: int) -> str:
    """Round-robin through the selected topics. Difficulty adaptation and
    weighted topic selection are Milestone 5 - this is deliberately the
    simplest thing that lets every selected topic get asked about."""
    return topics[index % len(topics)]


def _to_question_out(question_doc: dict) -> QuestionOut:
    return QuestionOut(
        id=str(question_doc["_id"]),
        index=question_doc["index"],
        topic=question_doc["topic"],
        difficulty=question_doc["difficulty"],
        question_text=question_doc["question_text"],
        concepts=question_doc["concepts"],
    )


class InterviewEngine:
    def __init__(self, db: AsyncIOMotorDatabase, llm: LLMClient):
        self._db = db
        self._llm = llm

    async def _to_interview_out(self, interview_doc: dict) -> InterviewOut:
        status = InterviewState(interview_doc["status"])
        current_question = None
        # Only expose a "current question" while one is actually pending an
        # answer - once COMPLETED/CANCELLED there's nothing to answer.
        if status == InterviewState.QUESTIONING:
            q_doc = await repo.get_question_by_index(
                self._db, interview_doc["_id"], interview_doc["current_question_index"]
            )
            if q_doc:
                current_question = _to_question_out(q_doc)

        return InterviewOut(
            id=str(interview_doc["_id"]),
            status=status,
            topics=interview_doc["topics"],
            difficulty=interview_doc["difficulty"],
            question_count=interview_doc["question_count"],
            current_question_index=interview_doc["current_question_index"],
            current_question=current_question,
            created_at=interview_doc["created_at"],
            completed_at=interview_doc.get("completed_at"),
        )

    async def _generate_and_store_question(self, interview_doc: dict, *, index: int) -> None:
        topic = _topic_for_index(interview_doc["topics"], index)
        previously_asked = await repo.get_asked_question_texts(self._db, interview_doc["_id"])

        generated = await self._llm.generate_question(
            topic=topic,
            difficulty=interview_doc["difficulty"],
            previously_asked=previously_asked,
        )
        await repo.insert_question(
            self._db,
            interview_id=interview_doc["_id"],
            index=index,
            topic=generated.topic,
            difficulty=generated.difficulty,
            question_text=generated.question,
            concepts=generated.concepts,
        )

    async def create_interview(self, request: CreateInterviewRequest) -> InterviewOut:
        interview_doc = await repo.create_interview(
            self._db,
            user_id=DEFAULT_USER_ID,
            topics=list(request.topics),
            difficulty=request.difficulty,
            question_count=request.question_count,
        )

        new_status = transition(InterviewState.SETUP, InterviewState.QUESTIONING)
        await self._generate_and_store_question(interview_doc, index=0)
        await repo.update_interview_status(self._db, interview_doc["_id"], new_status)

        interview_doc = await repo.get_interview(self._db, interview_doc["_id"])
        assert interview_doc is not None
        return await self._to_interview_out(interview_doc)

    async def get_interview(self, interview_id: str) -> InterviewOut:
        oid = parse_object_id(interview_id)
        interview_doc = await repo.get_interview(self._db, oid)
        if interview_doc is None:
            raise InterviewNotFoundError(interview_id)
        return await self._to_interview_out(interview_doc)

    async def submit_answer(self, interview_id: str, answer_text: str) -> SubmitAnswerResponse:
        oid = parse_object_id(interview_id)
        interview_doc = await repo.get_interview(self._db, oid)
        if interview_doc is None:
            raise InterviewNotFoundError(interview_id)

        current_status = InterviewState(interview_doc["status"])
        if current_status != InterviewState.QUESTIONING:
            raise InterviewNotActiveError(
                f"Interview is '{current_status}', not currently accepting answers"
            )

        index = interview_doc["current_question_index"]
        question_doc = await repo.get_question_by_index(self._db, oid, index)
        if question_doc is None:
            raise InterviewNotFoundError(f"No question at index {index} for interview {interview_id}")

        await repo.update_interview_status(
            self._db, oid, transition(current_status, InterviewState.EVALUATING)
        )

        answer_doc = await repo.insert_answer(
            self._db, interview_id=oid, question_id=question_doc["_id"], answer_text=answer_text
        )

        vague_flags = detect_vague_flags(answer_text)
        evaluation = await self._llm.evaluate_answer(
            question=question_doc["question_text"],
            topic=question_doc["topic"],
            difficulty=question_doc["difficulty"],
            answer_text=answer_text,
        )

        await repo.insert_evaluation(
            self._db,
            interview_id=oid,
            question_id=question_doc["_id"],
            answer_id=answer_doc["_id"],
            topic=question_doc["topic"],
            concepts=question_doc["concepts"],
            evaluation=evaluation,
            vague_flags=vague_flags,
        )

        next_index = index + 1
        is_last_question = next_index >= interview_doc["question_count"]

        if is_last_question:
            final_status = transition(InterviewState.EVALUATING, InterviewState.COMPLETED)
            await repo.update_interview_status(
                self._db,
                oid,
                final_status,
                current_question_index=next_index,
                completed_at=repo.now(),
            )
        else:
            # EVALUATING -> NEXT_QUESTION is a momentary bookkeeping state;
            # we generate the next question and land back in QUESTIONING
            # within the same request rather than exposing NEXT_QUESTION to
            # the client (there's nothing useful to show for it in a
            # synchronous text interview).
            transition(InterviewState.EVALUATING, InterviewState.NEXT_QUESTION)
            interview_doc["current_question_index"] = next_index
            await self._generate_and_store_question(interview_doc, index=next_index)
            resumed_status = transition(InterviewState.NEXT_QUESTION, InterviewState.QUESTIONING)
            await repo.update_interview_status(
                self._db, oid, resumed_status, current_question_index=next_index
            )

        interview_doc = await repo.get_interview(self._db, oid)
        assert interview_doc is not None
        return SubmitAnswerResponse(
            evaluation=EvaluationOut(scores=evaluation, vague_flags=vague_flags),
            interview=await self._to_interview_out(interview_doc),
        )

    async def get_report(self, interview_id: str) -> InterviewReport:
        oid = parse_object_id(interview_id)
        interview_doc = await repo.get_interview(self._db, oid)
        if interview_doc is None:
            raise InterviewNotFoundError(interview_id)

        questions = [_to_question_out(q) for q in await repo.list_questions(self._db, oid)]
        eval_docs = await repo.list_evaluations(self._db, oid)
        evaluations = [
            EvaluationOut(scores=AnswerEvaluation(**e["scores"]), vague_flags=e["vague_flags"])
            for e in eval_docs
        ]
        average_overall = (
            round(sum(e.scores.overall for e in evaluations) / len(evaluations), 2)
            if evaluations
            else 0.0
        )

        return InterviewReport(
            interview=await self._to_interview_out(interview_doc),
            questions=questions,
            evaluations=evaluations,
            average_overall=average_overall,
        )
