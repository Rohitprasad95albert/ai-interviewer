"""
StubLLMClient's deterministic approximation of resume structuring.

This is intentionally a simple, section-header-based heuristic, not a real
resume parser - its job is to be predictable enough to unit test and to let
the resume pipeline be built/verified without an API key, not to produce
production-quality extraction (that's what AnthropicLLMClient is for).
Language/framework/database detection is NOT attempted here - that's
app/resume/keyword_extractor.py's job, which runs regardless of which
LLMClient is active.
"""

from app.schemas.resume import CandidateProfile, Education, ExperienceEntry, ProjectEntry

_SECTION_HEADERS: dict[str, list[str]] = {
    "education": ["education", "academic background", "academics"],
    "projects": ["projects", "personal projects", "academic projects"],
    "experience": ["experience", "work experience", "internships", "internship"],
    "certifications": ["certifications", "certificates"],
    "achievements": ["achievements", "awards", "accomplishments"],
}

_HEADER_STRIP_CHARS = ":#-•* "


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {key: [] for key in _SECTION_HEADERS}
    current: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lowered = line.lower().strip(_HEADER_STRIP_CHARS)
        matched_section = next(
            (key for key, headers in _SECTION_HEADERS.items() if lowered in headers),
            None,
        )
        if matched_section:
            current = matched_section
            continue

        if current:
            sections[current].append(line)

    return sections


def extract_profile_heuristically(resume_text: str) -> CandidateProfile:
    sections = _split_sections(resume_text)

    education = [Education(institution=line[:200]) for line in sections["education"]]
    certifications = list(sections["certifications"])
    achievements = list(sections["achievements"])
    projects = [
        ProjectEntry(name=line[:80], description=line) for line in sections["projects"]
    ]
    experience = [
        ExperienceEntry(organization=line[:80], role="", description=line)
        for line in sections["experience"]
    ]

    return CandidateProfile(
        education=education,
        projects=projects,
        experience=experience,
        certifications=certifications,
        achievements=achievements,
        # programming_languages/frameworks/databases/technologies/skills
        # intentionally left empty here - keyword_extractor.py supplies
        # the deterministic tech fields, merged in by resume/service.py.
    )


# Re-exported for tests that want to assert on section splitting directly
# without going through the full CandidateProfile shape.
split_sections_for_testing = _split_sections
