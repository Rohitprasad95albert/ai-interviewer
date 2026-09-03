"""
Covers the profile merge logic and stub section-splitting as fast pure-logic
unit tests, then the full upload -> extract -> structure -> persist -> list
-> get -> delete flow as integration tests through the real API against a
real MongoDB test database (same pattern as test_interview_flow.py),
running against the StubLLMClient since no ANTHROPIC_API_KEY is set here.
"""

from fastapi.testclient import TestClient

from app.ai.stub_resume_extractor import extract_profile_heuristically, split_sections_for_testing
from app.main import app
from app.resume.profile_merger import merge_profile
from app.schemas.resume import CandidateProfile
from tests.resume_fixtures import corrupt_pdf_bytes, sample_resume_pdf_bytes

# --- profile_merger (pure, no DB) ---------------------------------------


def test_merge_unions_keyword_and_llm_technology_findings():
    keyword_findings = {
        "programming_languages": ["Python"],
        "frameworks": ["FastAPI"],
        "databases": ["MongoDB"],
        "technologies": ["AWS"],
    }
    llm_profile = CandidateProfile(
        programming_languages=["Python", "Go"],  # overlaps with keyword findings
        frameworks=["Django"],
    )

    merged = merge_profile(keyword_findings, llm_profile)

    assert set(merged.programming_languages) == {"Python", "Go"}
    assert set(merged.frameworks) == {"FastAPI", "Django"}
    assert merged.databases == ["MongoDB"]
    assert merged.technologies == ["AWS"]


def test_merge_dedups_case_insensitively_keeping_keyword_matcher_casing():
    keyword_findings = {
        "programming_languages": ["Python"],
        "frameworks": [],
        "databases": [],
        "technologies": [],
    }
    llm_profile = CandidateProfile(programming_languages=["python"])  # same, different case

    merged = merge_profile(keyword_findings, llm_profile)

    assert merged.programming_languages == ["Python"]


def test_merge_takes_narrative_fields_entirely_from_llm():
    llm_profile = CandidateProfile(
        skills=["Leadership"],
        certifications=["AWS Certified"],
        achievements=["Hackathon winner"],
    )
    merged = merge_profile(
        {"programming_languages": [], "frameworks": [], "databases": [], "technologies": []},
        llm_profile,
    )
    assert merged.skills == ["Leadership"]
    assert merged.certifications == ["AWS Certified"]
    assert merged.achievements == ["Hackathon winner"]


# --- stub section splitting (pure, no DB) --------------------------------


def test_stub_splits_sections_by_header():
    text = "EDUCATION\nABC University\nPROJECTS\nCool Project"
    sections = split_sections_for_testing(text)
    assert sections["education"] == ["ABC University"]
    assert sections["projects"] == ["Cool Project"]


def test_stub_ignores_lines_before_first_header():
    text = "Jane Doe\njane@example.com\nEDUCATION\nABC University"
    sections = split_sections_for_testing(text)
    assert sections["education"] == ["ABC University"]


def test_stub_extract_profile_produces_education_and_certifications():
    text = "EDUCATION\nABC University\nCERTIFICATIONS\nAWS Certified"
    profile = extract_profile_heuristically(text)
    assert profile.education[0].institution == "ABC University"
    assert profile.certifications == ["AWS Certified"]


# --- full pipeline, real API + real MongoDB test DB ----------------------


def test_upload_valid_pdf_extracts_and_structures_a_profile():
    with TestClient(app) as client:
        response = client.post(
            "/api/resumes",
            files={"file": ("resume.pdf", sample_resume_pdf_bytes(), "application/pdf")},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "extracted"
        assert body["filename"] == "resume.pdf"
        assert body["profile"] is not None
        assert "Python" in body["profile"]["programming_languages"]
        assert "MongoDB" in body["profile"]["databases"]
        assert len(body["profile"]["education"]) >= 1
        assert len(body["profile"]["certifications"]) >= 1


def test_upload_corrupt_pdf_is_stored_as_failed_not_500():
    with TestClient(app) as client:
        response = client.post(
            "/api/resumes",
            files={"file": ("broken.pdf", corrupt_pdf_bytes(), "application/pdf")},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "failed"
        assert body["profile"] is None
        assert body["extraction_error"] is not None
        # Never leak raw parser exception text
        assert "Traceback" not in body["extraction_error"]


def test_upload_non_pdf_is_rejected_with_400():
    with TestClient(app) as client:
        response = client.post(
            "/api/resumes",
            files={"file": ("resume.png", b"not a real image either", "image/png")},
        )
        assert response.status_code == 400


def test_list_get_and_delete_resume_flow():
    with TestClient(app) as client:
        upload = client.post(
            "/api/resumes",
            files={"file": ("resume.pdf", sample_resume_pdf_bytes(), "application/pdf")},
        ).json()
        resume_id = upload["id"]

        listing = client.get("/api/resumes").json()
        assert any(r["id"] == resume_id for r in listing)

        detail = client.get(f"/api/resumes/{resume_id}")
        assert detail.status_code == 200
        assert detail.json()["id"] == resume_id

        delete_response = client.delete(f"/api/resumes/{resume_id}")
        assert delete_response.status_code == 204

        after_delete = client.get(f"/api/resumes/{resume_id}")
        assert after_delete.status_code == 404


def test_get_unknown_resume_returns_404():
    with TestClient(app) as client:
        response = client.get("/api/resumes/000000000000000000000000")
        assert response.status_code == 404


def test_get_malformed_resume_id_returns_404_not_500():
    with TestClient(app) as client:
        response = client.get("/api/resumes/not-a-valid-object-id")
        assert response.status_code == 404
