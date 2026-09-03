"""
Interview endpoints - Milestone 2 (Technical Interview only, fixed
question count, no adaptivity yet).
"""

from fastapi import APIRouter, Depends, HTTPException

from app.ai.factory import get_llm_client
from app.db.mongodb import get_database
from app.interview.engine import InterviewEngine, InterviewNotActiveError, InterviewNotFoundError
from app.schemas.interview import (
    CreateInterviewRequest,
    InterviewOut,
    InterviewReport,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)

router = APIRouter()


def get_engine() -> InterviewEngine:
    return InterviewEngine(db=get_database(), llm=get_llm_client())


@router.post("/interviews", response_model=InterviewOut, status_code=201)
async def create_interview(
    request: CreateInterviewRequest, engine: InterviewEngine = Depends(get_engine)
) -> InterviewOut:
    """Start a new interview: creates it and generates the first question."""
    return await engine.create_interview(request)


@router.get("/interviews/{interview_id}", response_model=InterviewOut)
async def get_interview(
    interview_id: str, engine: InterviewEngine = Depends(get_engine)
) -> InterviewOut:
    try:
        return await engine.get_interview(interview_id)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Interview not found") from exc


@router.post("/interviews/{interview_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    interview_id: str,
    request: SubmitAnswerRequest,
    engine: InterviewEngine = Depends(get_engine),
) -> SubmitAnswerResponse:
    """
    Submit an answer to the current question. Evaluates it, stores the
    evaluation, and returns either the next question or the completed
    interview (check `interview.status`).
    """
    try:
        return await engine.submit_answer(interview_id, request.answer_text)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Interview not found") from exc
    except InterviewNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/interviews/{interview_id}/report", response_model=InterviewReport)
async def get_report(
    interview_id: str, engine: InterviewEngine = Depends(get_engine)
) -> InterviewReport:
    try:
        return await engine.get_report(interview_id)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Interview not found") from exc
