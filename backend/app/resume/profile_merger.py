"""
Combines the deterministic keyword matcher's findings with the LLM's
structuring pass into one CandidateProfile. Pure function - no DB, no LLM
call here - so it's directly unit-testable (see tests/test_resume_service.py).
"""

from app.schemas.resume import CandidateProfile


def _dedup_merge(*lists: list[str]) -> list[str]:
    """Union multiple lists, case-insensitive dedup, first-seen casing wins."""
    seen: dict[str, str] = {}
    for lst in lists:
        for item in lst:
            cleaned = item.strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if key not in seen:
                seen[key] = cleaned
    return list(seen.values())


def merge_profile(
    keyword_findings: dict[str, list[str]], llm_profile: CandidateProfile
) -> CandidateProfile:
    """
    Technology fields are the union of the keyword matcher's (controlled,
    reliable) findings and whatever the LLM additionally noticed - the
    keyword matcher's canonical spelling wins on a case-insensitive
    collision. Narrative fields (education/projects/experience/
    certifications/achievements/skills) come entirely from the LLM pass -
    a keyword list can't meaningfully extract those.
    """
    return CandidateProfile(
        education=llm_profile.education,
        programming_languages=_dedup_merge(
            keyword_findings.get("programming_languages", []), llm_profile.programming_languages
        ),
        frameworks=_dedup_merge(keyword_findings.get("frameworks", []), llm_profile.frameworks),
        databases=_dedup_merge(keyword_findings.get("databases", []), llm_profile.databases),
        technologies=_dedup_merge(
            keyword_findings.get("technologies", []), llm_profile.technologies
        ),
        skills=llm_profile.skills,
        projects=llm_profile.projects,
        experience=llm_profile.experience,
        certifications=llm_profile.certifications,
        achievements=llm_profile.achievements,
    )
