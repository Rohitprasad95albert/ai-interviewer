"""
OpenRouterLLMClient tests using a fake AsyncOpenAI-shaped client - no real
HTTP calls, no OPENROUTER_API_KEY required. Covers structured-output
success/retry/failure, and translation of each openai.* exception into our
provider-agnostic error types (app/ai/errors.py).

The one real-API test (requires OPENROUTER_API_KEY) lives in
test_openrouter_live.py and is auto-skipped when the key isn't set.
"""

import json
from types import SimpleNamespace

import httpx2
import openai
import pytest

from app.ai.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.ai.openrouter_client import OpenRouterLLMClient
from app.schemas.interview import GeneratedQuestion


def fake_completion(content: str | None):
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


class FakeCompletions:
    """Returns each item from `responses` in order on successive .create() calls."""

    def __init__(self, responses: list):
        self._responses = iter(responses)
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        item = next(self._responses)
        if isinstance(item, Exception):
            raise item
        return item


class FakeAsyncOpenAI:
    def __init__(self, responses: list):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


def _dummy_request() -> httpx2.Request:
    return httpx2.Request("POST", "https://openrouter.ai/api/v1/chat/completions")


def _status_error(cls, status: int, message: str = "error"):
    response = httpx2.Response(status, request=_dummy_request())
    return cls(message, response=response, body=None)


VALID_QUESTION_JSON = json.dumps(
    {"question": "Explain X", "topic": "dsa", "difficulty": "medium", "concepts": ["x"]}
)


@pytest.mark.asyncio
async def test_successful_structured_output_on_first_try():
    fake_client = FakeAsyncOpenAI([fake_completion(VALID_QUESTION_JSON)])
    client = OpenRouterLLMClient(client=fake_client)

    result = await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])

    assert isinstance(result, GeneratedQuestion)
    assert result.question == "Explain X"
    # Model comes from settings, not hardcoded in the call
    assert fake_client.chat.completions.calls[0]["model"] == client._model


@pytest.mark.asyncio
async def test_retries_once_on_malformed_json_then_succeeds():
    fake_client = FakeAsyncOpenAI(
        [fake_completion("not valid json at all"), fake_completion(VALID_QUESTION_JSON)]
    )
    client = OpenRouterLLMClient(client=fake_client)

    result = await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])

    assert result.question == "Explain X"
    assert len(fake_client.chat.completions.calls) == 2


@pytest.mark.asyncio
async def test_raises_invalid_response_error_after_exhausting_retries_on_bad_json():
    fake_client = FakeAsyncOpenAI(
        [fake_completion("still not json"), fake_completion("still not json either")]
    )
    client = OpenRouterLLMClient(client=fake_client)

    with pytest.raises(LLMInvalidResponseError):
        await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])


@pytest.mark.asyncio
async def test_raises_invalid_response_error_on_json_that_fails_schema_validation():
    bad_shape = json.dumps({"question": "Explain X"})  # missing required fields
    fake_client = FakeAsyncOpenAI([fake_completion(bad_shape), fake_completion(bad_shape)])
    client = OpenRouterLLMClient(client=fake_client)

    with pytest.raises(LLMInvalidResponseError):
        await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])


@pytest.mark.asyncio
async def test_empty_response_content_triggers_retry():
    fake_client = FakeAsyncOpenAI(
        [fake_completion(None), fake_completion(VALID_QUESTION_JSON)]
    )
    client = OpenRouterLLMClient(client=fake_client)

    result = await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])
    assert result.question == "Explain X"


@pytest.mark.asyncio
async def test_authentication_error_is_translated():
    fake_client = FakeAsyncOpenAI([_status_error(openai.AuthenticationError, 401)])
    client = OpenRouterLLMClient(client=fake_client)

    with pytest.raises(LLMAuthenticationError):
        await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])


@pytest.mark.asyncio
async def test_rate_limit_error_is_translated():
    fake_client = FakeAsyncOpenAI([_status_error(openai.RateLimitError, 429)])
    client = OpenRouterLLMClient(client=fake_client)

    with pytest.raises(LLMRateLimitError):
        await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])


@pytest.mark.asyncio
async def test_timeout_error_is_translated():
    fake_client = FakeAsyncOpenAI([openai.APITimeoutError(request=_dummy_request())])
    client = OpenRouterLLMClient(client=fake_client)

    with pytest.raises(LLMTimeoutError):
        await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])


@pytest.mark.asyncio
async def test_connection_error_is_translated():
    fake_client = FakeAsyncOpenAI([openai.APIConnectionError(request=_dummy_request())])
    client = OpenRouterLLMClient(client=fake_client)

    with pytest.raises(LLMConnectionError):
        await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])


@pytest.mark.asyncio
async def test_generic_api_status_error_is_translated():
    fake_client = FakeAsyncOpenAI([_status_error(openai.APIStatusError, 502, "bad gateway")])
    client = OpenRouterLLMClient(client=fake_client)

    with pytest.raises(LLMProviderError):
        await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])


@pytest.mark.asyncio
async def test_provider_errors_never_include_the_api_key_in_their_message():
    from app.core.config import settings

    fake_client = FakeAsyncOpenAI([_status_error(openai.AuthenticationError, 401)])
    client = OpenRouterLLMClient(client=fake_client)

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])

    assert settings.openrouter_api_key not in str(exc_info.value)


@pytest.mark.asyncio
async def test_all_four_llmclient_methods_are_implemented():
    """OpenRouterLLMClient must implement every LLMClient method (spec requirement)."""
    from app.schemas.interview import AnswerEvaluation
    from app.schemas.resume import CandidateProfile

    eval_json = json.dumps(
        {
            "technical_accuracy": 7,
            "depth": 7,
            "completeness": 7,
            "clarity": 7,
            "relevance": 7,
            "communication": 7,
            "overall": 7.0,
            "strengths": [],
            "weaknesses": [],
            "missing_concepts": [],
            "follow_up_recommended": False,
            "follow_up_reason": "",
            "suggested_next_difficulty": "medium",
        }
    )
    profile_json = json.dumps({})  # every CandidateProfile field has a default

    fake_client = FakeAsyncOpenAI(
        [
            fake_completion(VALID_QUESTION_JSON),  # generate_question
            fake_completion(eval_json),  # evaluate_answer
            fake_completion(VALID_QUESTION_JSON),  # generate_follow_up_question
            fake_completion(profile_json),  # extract_candidate_profile
        ]
    )
    client = OpenRouterLLMClient(client=fake_client)

    q = await client.generate_question(topic="dsa", difficulty="medium", previously_asked=[])
    assert isinstance(q, GeneratedQuestion)

    e = await client.evaluate_answer(
        question="Q", topic="dsa", difficulty="medium", answer_text="A"
    )
    assert isinstance(e, AnswerEvaluation)

    f = await client.generate_follow_up_question(
        original_question="Q",
        original_answer="A",
        topic="dsa",
        difficulty="medium",
        weaknesses=[],
        vague_flags=[],
    )
    assert isinstance(f, GeneratedQuestion)

    p = await client.extract_candidate_profile(resume_text="some resume text")
    assert isinstance(p, CandidateProfile)
