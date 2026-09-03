"""
Optional real-API integration tests against the live OpenRouter API.
Auto-skipped unless OPENROUTER_API_KEY is set (checked at collection time,
not import time, so this file is always safe to collect) - the rest of the
test suite never requires a real key. These make real network calls and
spend real API credits when they run.
"""

import pytest

from app.core.config import settings

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not settings.openrouter_api_key,
        reason="OPENROUTER_API_KEY not set - skipping live OpenRouter tests",
    ),
]


@pytest.fixture
def client():
    from app.ai.openrouter_client import OpenRouterLLMClient

    return OpenRouterLLMClient()


@pytest.mark.asyncio
async def test_generate_question_against_real_openrouter(client):
    result = await client.generate_question(
        topic="dsa", difficulty="easy", previously_asked=[]
    )
    assert result.question.strip()
    assert result.topic == "dsa"
    assert result.difficulty == "easy"


@pytest.mark.asyncio
async def test_evaluate_answer_against_real_openrouter(client):
    result = await client.evaluate_answer(
        question="What is the time complexity of binary search?",
        topic="dsa",
        difficulty="easy",
        answer_text="O(log n), because each step halves the remaining search space.",
    )
    assert 0 <= result.overall <= 10
    assert 0 <= result.technical_accuracy <= 10


@pytest.mark.asyncio
async def test_generate_follow_up_against_real_openrouter(client):
    result = await client.generate_follow_up_question(
        original_question="Why did you choose MongoDB?",
        original_answer="Because it's scalable.",
        topic="dbms",
        difficulty="medium",
        weaknesses=["Answer relies on an unexplained buzzword."],
        vague_flags=['Unexplained buzzword justification: "because it is scalable"'],
    )
    assert result.question.strip()


@pytest.mark.asyncio
async def test_extract_candidate_profile_against_real_openrouter(client):
    resume_text = (
        "Jane Doe\n\n"
        "EDUCATION\nABC Institute of Technology - B.Tech Computer Science, 2022-2026\n\n"
        "PROJECTS\nAI Interviewer - Built with Python, FastAPI, and MongoDB.\n\n"
        "CERTIFICATIONS\nAWS Certified Cloud Practitioner\n"
    )
    profile = await client.extract_candidate_profile(resume_text=resume_text)
    assert isinstance(profile.education, list)
    assert isinstance(profile.projects, list)
