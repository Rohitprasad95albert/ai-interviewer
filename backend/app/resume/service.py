"""
Resume ingestion pipeline orchestrator - the only place that ties together
validation, deterministic text extraction, deterministic keyword matching,
LLM structuring, merging, and persistence.

Deliberately mirrors app/interview/engine.py's shape: plain Python controls
the sequence and decides what happens on failure; the LLMClient is one
interchangeable step in the middle, never in control of it (spec section 23).
"""

import logging

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai.base import LLMClient
from app.resume import repository as repo
from app.resume.extractors.base import ExtractionError, UnsupportedFileTypeError, get_extractor
from app.resume.keyword_extractor import extract_known_technologies
from app.resume.profile_merger import merge_profile
from app.resume.validation import validate_upload
from app.schemas.resume import ResumeOut, ResumeSummaryOut

logger = logging.getLogger(__name__)

# Matches app/interview/engine.py's DEFAULT_USER_ID - single-user for now
# (auth is Milestone 9); kept as its own constant here rather than imported
# from the interview module so the resume domain doesn't depend on it.
DEFAULT_USER_ID = "default-user"


class ResumeNotFoundError(Exception):
    pass


def parse_object_id(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except InvalidId as exc:
        raise ResumeNotFoundError(raw_id) from exc


def _to_resume_out(doc: dict) -> ResumeOut:
    return ResumeOut(
        id=str(doc["_id"]),
        filename=doc["filename"],
        content_type=doc["content_type"],
        file_size_bytes=doc["file_size_bytes"],
        status=doc["status"],
        extraction_error=doc.get("extraction_error"),
        profile=doc.get("profile"),
        uploaded_at=doc["uploaded_at"],
        extracted_at=doc.get("extracted_at"),
    )


def _to_resume_summary(doc: dict) -> ResumeSummaryOut:
    return ResumeSummaryOut(
        id=str(doc["_id"]),
        filename=doc["filename"],
        status=doc["status"],
        uploaded_at=doc["uploaded_at"],
    )


class ResumeService:
    def __init__(self, db: AsyncIOMotorDatabase, llm: LLMClient):
        self._db = db
        self._llm = llm

    async def upload_and_process(
        self, *, filename: str, content_type: str | None, file_bytes: bytes
    ) -> ResumeOut:
        # Raises ResumeValidationError on bad type/size/empty/magic-bytes -
        # the route layer maps that to a 400. Nothing is persisted yet.
        validate_upload(content_type=content_type, file_bytes=file_bytes)
        assert content_type is not None  # validate_upload already rejected None

        resume_doc = await repo.create_resume(
            self._db,
            user_id=DEFAULT_USER_ID,
            filename=filename,
            content_type=content_type,
            file_size_bytes=len(file_bytes),
            raw_bytes=file_bytes,
        )
        resume_id = resume_doc["_id"]

        try:
            extractor = get_extractor(content_type)
            raw_text = extractor.extract(file_bytes)
        except (ExtractionError, UnsupportedFileTypeError) as exc:
            # Log only the exception type/class - never str(exc) content
            # into logs, and store only the already-generic message on the
            # document (never the underlying parser's raw error).
            logger.warning(
                "Resume extraction failed (resume_id=%s): %s", resume_id, type(exc).__name__
            )
            await repo.mark_failed(self._db, resume_id, error_message=str(exc))
            failed_doc = await repo.get_resume(self._db, resume_id)
            assert failed_doc is not None
            return _to_resume_out(failed_doc)

        keyword_findings = extract_known_technologies(raw_text)
        llm_profile = await self._llm.extract_candidate_profile(resume_text=raw_text)
        profile = merge_profile(keyword_findings, llm_profile)

        await repo.mark_extracted(self._db, resume_id, raw_text=raw_text, profile=profile)
        extracted_doc = await repo.get_resume(self._db, resume_id)
        assert extracted_doc is not None
        return _to_resume_out(extracted_doc)

    async def get_resume(self, resume_id: str) -> ResumeOut:
        oid = parse_object_id(resume_id)
        doc = await repo.get_resume(self._db, oid)
        if doc is None:
            raise ResumeNotFoundError(resume_id)
        return _to_resume_out(doc)

    async def list_resumes(self) -> list[ResumeSummaryOut]:
        docs = await repo.list_resumes(self._db, DEFAULT_USER_ID)
        return [_to_resume_summary(d) for d in docs]

    async def delete_resume(self, resume_id: str) -> None:
        oid = parse_object_id(resume_id)
        deleted = await repo.delete_resume(self._db, oid)
        if not deleted:
            raise ResumeNotFoundError(resume_id)
