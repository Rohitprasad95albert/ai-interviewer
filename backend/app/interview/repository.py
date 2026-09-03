"""
MongoDB access for the interview domain. Kept separate from engine.py so the
orchestration logic (engine.py) reads as business logic, not query code.

Collections (spec section 21):
- interviews          one doc per interview session
- interview_questions one doc per question asked, referencing interview_id
- answers             one doc per submitted answer, referencing question_id
- evaluations         one doc per evaluation, referencing interview_id/question_id

`topic` and `concepts` are deliberately duplicated onto each evaluation
document (denormalized from the question). This is a conscious exception to
"don't duplicate data" (spec section 21): Milestone 6 (recurring weakness
detection) needs to aggregate evaluations by topic across potentially
hundreds of interviews, and denormalizing avoids a $lookup join on that
hot path. Everything else follows normal references.
"""

from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.interview import AnswerEvaluation, InterviewState


def now() -> datetime:
    return datetime.now(UTC)


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Called once at startup (see main.py lifespan). Safe to call repeatedly -
    create_index is idempotent.
    """
    # Look up "my interviews" (history, Milestone 3) by user.
    await db.interviews.create_index("user_id")
    # Fetch all questions/answers/evaluations for one interview - the most
    # common query shape in this app (every report/live-interview screen).
    await db.interview_questions.create_index("interview_id")
    await db.answers.create_index("interview_id")
    # One answer per question in this milestone (no answer editing yet).
    await db.answers.create_index("question_id", unique=True)
    await db.evaluations.create_index("interview_id")
    # Powers Milestone 6's "which topics does this candidate struggle with
    # across all interviews" aggregation.
    await db.evaluations.create_index("topic")


async def create_interview(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    topics: list[str],
    difficulty: str,
    question_count: int,
) -> dict:
    doc = {
        "user_id": user_id,
        "mode": "technical",
        "topics": topics,
        "difficulty": difficulty,
        "current_difficulty": difficulty,  # adapts over the session (spec section 8)
        "consecutive_follow_ups": 0,  # caps how many follow-ups can chain in a row
        "question_count": question_count,
        "status": InterviewState.SETUP.value,
        "current_question_index": 0,
        "created_at": now(),
        "updated_at": now(),
        "completed_at": None,
    }
    result = await db.interviews.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_interview(db: AsyncIOMotorDatabase, interview_id: ObjectId) -> dict | None:
    return await db.interviews.find_one({"_id": interview_id})


async def update_interview_status(
    db: AsyncIOMotorDatabase,
    interview_id: ObjectId,
    status: InterviewState,
    **extra_fields,
) -> None:
    fields = {"status": status.value, "updated_at": now(), **extra_fields}
    await db.interviews.update_one({"_id": interview_id}, {"$set": fields})


async def insert_question(
    db: AsyncIOMotorDatabase,
    *,
    interview_id: ObjectId,
    index: int,
    topic: str,
    difficulty: str,
    question_text: str,
    concepts: list[str],
    is_follow_up: bool = False,
    parent_question_id: ObjectId | None = None,
) -> dict:
    doc = {
        "interview_id": interview_id,
        "index": index,
        "topic": topic,
        "difficulty": difficulty,
        "question_text": question_text,
        "concepts": concepts,
        "is_follow_up": is_follow_up,
        "parent_question_id": parent_question_id,
        "created_at": now(),
    }
    result = await db.interview_questions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_question_by_index(
    db: AsyncIOMotorDatabase, interview_id: ObjectId, index: int
) -> dict | None:
    return await db.interview_questions.find_one(
        {"interview_id": interview_id, "index": index}
    )


async def list_questions(db: AsyncIOMotorDatabase, interview_id: ObjectId) -> list[dict]:
    cursor = db.interview_questions.find({"interview_id": interview_id}).sort("index", 1)
    return await cursor.to_list(length=None)


async def get_asked_question_texts(
    db: AsyncIOMotorDatabase, interview_id: ObjectId
) -> list[str]:
    questions = await list_questions(db, interview_id)
    return [q["question_text"] for q in questions]


async def insert_answer(
    db: AsyncIOMotorDatabase, *, interview_id: ObjectId, question_id: ObjectId, answer_text: str
) -> dict:
    doc = {
        "interview_id": interview_id,
        "question_id": question_id,
        "answer_text": answer_text,
        "submitted_at": now(),
    }
    result = await db.answers.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def insert_evaluation(
    db: AsyncIOMotorDatabase,
    *,
    interview_id: ObjectId,
    question_id: ObjectId,
    answer_id: ObjectId,
    topic: str,
    concepts: list[str],
    evaluation: AnswerEvaluation,
    vague_flags: list[str],
) -> dict:
    doc = {
        "interview_id": interview_id,
        "question_id": question_id,
        "answer_id": answer_id,
        "topic": topic,
        "concepts": concepts,
        "scores": evaluation.model_dump(),
        "vague_flags": vague_flags,
        "created_at": now(),
    }
    result = await db.evaluations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_evaluations(db: AsyncIOMotorDatabase, interview_id: ObjectId) -> list[dict]:
    cursor = db.evaluations.find({"interview_id": interview_id}).sort("created_at", 1)
    return await cursor.to_list(length=None)
