"""Resume upload/list/detail/delete endpoints (Milestone 4)."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.ai.factory import get_llm_client
from app.db.mongodb import get_database
from app.resume.service import ResumeNotFoundError, ResumeService
from app.resume.validation import ResumeValidationError
from app.schemas.resume import ResumeOut, ResumeSummaryOut

router = APIRouter()


def get_service() -> ResumeService:
    return ResumeService(db=get_database(), llm=get_llm_client())


@router.post("/resumes", response_model=ResumeOut, status_code=201)
async def upload_resume(
    file: UploadFile = File(...), service: ResumeService = Depends(get_service)
) -> ResumeOut:
    """
    Upload a resume (PDF only for now). Always returns 201 if the upload
    itself was well-formed - a parsing failure is reflected in the
    response body as status="failed" with a generic extraction_error,
    not a 4xx/5xx, since the resume record itself was still created.
    """
    file_bytes = await file.read()
    try:
        return await service.upload_and_process(
            filename=file.filename or "resume.pdf",
            content_type=file.content_type,
            file_bytes=file_bytes,
        )
    except ResumeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/resumes", response_model=list[ResumeSummaryOut])
async def list_resumes(service: ResumeService = Depends(get_service)) -> list[ResumeSummaryOut]:
    return await service.list_resumes()


@router.get("/resumes/{resume_id}", response_model=ResumeOut)
async def get_resume(resume_id: str, service: ResumeService = Depends(get_service)) -> ResumeOut:
    try:
        return await service.get_resume(resume_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Resume not found") from exc


@router.delete("/resumes/{resume_id}", status_code=204)
async def delete_resume(resume_id: str, service: ResumeService = Depends(get_service)) -> None:
    try:
        await service.delete_resume(resume_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Resume not found") from exc
