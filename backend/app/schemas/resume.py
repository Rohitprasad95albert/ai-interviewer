"""
Resume ingestion schemas (Milestone 4).

CandidateProfile is deliberately separate from the interview-performance
"candidate profile" described in spec section 14 (DSA 7.2, OOP 8.1, ...,
derived from interview history - Milestone 6). This one is derived from a
resume's contents. To avoid confusing the two under one name, this stays
embedded on the ResumeDocument rather than living in its own
`candidate_profiles` collection - that collection name is reserved for the
Milestone 6 concept instead.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Education(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_year: str | None = None
    end_year: str | None = None


class ProjectEntry(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    organization: str
    role: str
    duration: str | None = None
    description: str | None = None


class CandidateProfile(BaseModel):
    """
    The structured shape extracted from a resume. Populated by two
    independent sources merged together (see app/resume/service.py):
    a deterministic keyword matcher (programming_languages, frameworks,
    databases, technologies) and an LLM structuring pass (everything else,
    plus additional technology mentions the keyword list didn't cover).
    """

    education: list[Education] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)


class ResumeStatus(StrEnum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    FAILED = "failed"


class ResumeOut(BaseModel):
    id: str
    filename: str
    content_type: str
    file_size_bytes: int
    status: ResumeStatus
    extraction_error: str | None = None
    profile: CandidateProfile | None = None
    uploaded_at: datetime
    extracted_at: datetime | None = None


class ResumeSummaryOut(BaseModel):
    """Lighter shape for list views - omits the (potentially large) profile."""

    id: str
    filename: str
    status: ResumeStatus
    uploaded_at: datetime
