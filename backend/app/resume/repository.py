"""
MongoDB access for the `resumes` collection.

`raw_bytes` is kept (not just the extracted text) so a future extraction
pipeline improvement or DOCX/OCR support can reprocess an existing upload
without asking the user to re-upload. At the enforced 5MB upload cap this
stays well under MongoDB's 16MB document size limit; if that cap ever grows
substantially, GridFS would be the next step - noted here rather than
built now, since it's not needed yet.
"""

from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.resume import CandidateProfile, ResumeStatus


def now() -> datetime:
    return datetime.now(UTC)


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    # List "my resumes" (most recent first) and delete-by-id are the only
    # query patterns today.
    await db.resumes.create_index("user_id")


async def create_resume(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    filename: str,
    content_type: str,
    file_size_bytes: int,
    raw_bytes: bytes,
) -> dict:
    doc = {
        "user_id": user_id,
        "filename": filename,
        "content_type": content_type,
        "file_size_bytes": file_size_bytes,
        "raw_bytes": raw_bytes,
        "raw_text": None,
        "status": ResumeStatus.UPLOADED.value,
        "extraction_error": None,
        "profile": None,
        "uploaded_at": now(),
        "extracted_at": None,
    }
    result = await db.resumes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def mark_extracted(
    db: AsyncIOMotorDatabase, resume_id: ObjectId, *, raw_text: str, profile: CandidateProfile
) -> None:
    await db.resumes.update_one(
        {"_id": resume_id},
        {
            "$set": {
                "status": ResumeStatus.EXTRACTED.value,
                "raw_text": raw_text,
                "profile": profile.model_dump(),
                "extracted_at": now(),
                "extraction_error": None,
            }
        },
    )


async def mark_failed(db: AsyncIOMotorDatabase, resume_id: ObjectId, *, error_message: str) -> None:
    await db.resumes.update_one(
        {"_id": resume_id},
        {
            "$set": {
                "status": ResumeStatus.FAILED.value,
                "extraction_error": error_message,
                "extracted_at": now(),
            }
        },
    )


async def get_resume(db: AsyncIOMotorDatabase, resume_id: ObjectId) -> dict | None:
    return await db.resumes.find_one({"_id": resume_id})


async def list_resumes(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    cursor = db.resumes.find({"user_id": user_id}).sort("uploaded_at", -1)
    return await cursor.to_list(length=None)


async def delete_resume(db: AsyncIOMotorDatabase, resume_id: ObjectId) -> bool:
    result = await db.resumes.delete_one({"_id": resume_id})
    return result.deleted_count > 0
