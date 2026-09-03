"""
Real LLM client backed by OpenRouter (https://openrouter.ai), an
OpenAI-API-compatible proxy in front of many model providers. Uses the
official `openai` Python SDK pointed at OpenRouter's base_url - this is
OpenRouter's own documented integration approach (verified against current
OpenRouter docs), not a hand-rolled HTTP client.

Implements the same LLMClient protocol as StubLLMClient/AnthropicLLMClient
(app/ai/base.py). The interview engine and resume service never import this
module directly (see app/ai/factory.py) - no OpenRouter-specific concept
(model slugs, response_format shape, error codes) leaks outside this file.

Structured output: requests OpenRouter's documented
`response_format: {"type": "json_schema", ...}` (derived from each Pydantic
schema) as a hint to the model, but never trusts it blindly - the response
is independently `json.loads`'d and Pydantic-validated before being
returned, exactly the same schemas the Anthropic/stub clients return. One
retry with corrective feedback is attempted on a parse/validation failure;
a second failure raises LLMInvalidResponseError rather than propagating a
raw parsing exception.
"""

import json
import logging
from typing import TypeVar

import openai
from pydantic import BaseModel, ValidationError

from app.ai.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.ai.prompt_builder import (
    build_evaluation_prompt,
    build_follow_up_prompt,
    build_question_prompt,
    build_resume_extraction_prompt,
)
from app.core.config import settings
from app.schemas.interview import AnswerEvaluation, Difficulty, GeneratedQuestion, Topic
from app.schemas.resume import CandidateProfile

logger = logging.getLogger(__name__)

_MAX_STRUCTURED_OUTPUT_ATTEMPTS = 2

_SchemaT = TypeVar("_SchemaT", bound=BaseModel)


class OpenRouterLLMClient:
    def __init__(self, client: openai.AsyncOpenAI | None = None) -> None:
        # The `openai` SDK is OpenRouter's own documented client - pointing
        # its base_url at OpenRouter is the whole integration; no custom
        # HTTP/auth code needed. max_retries covers transient network/5xx
        # failures at the SDK level; our own retry loop below is only for
        # schema-invalid *content*, a different failure mode.
        #
        # `client` is injectable so tests can pass a mock instead of ever
        # making a real HTTP call - see tests/test_openrouter_client.py.
        self._client = client or openai.AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=settings.openrouter_timeout_seconds,
            max_retries=2,
        )
        self._model = settings.openrouter_model

    async def _complete_structured(self, prompt: str, schema: type[_SchemaT]) -> _SchemaT:
        schema_dict = schema.model_json_schema()
        schema_dict["additionalProperties"] = False
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": schema_dict},
        }

        messages: list[dict] = [{"role": "user", "content": prompt}]
        last_error: Exception | None = None

        for attempt in range(1, _MAX_STRUCTURED_OUTPUT_ATTEMPTS + 1):
            completion = await self._create_completion(messages, response_format)

            content = completion.choices[0].message.content if completion.choices else None
            if not content:
                last_error = LLMInvalidResponseError("OpenRouter returned an empty response.")
                messages = [
                    *messages,
                    {
                        "role": "user",
                        "content": "Your response was empty. Reply with ONLY valid JSON "
                        "matching the requested schema.",
                    },
                ]
                continue

            try:
                data = json.loads(content)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                # Never log `content` or `prompt` - may contain resume/
                # answer text. Log only the failure type and attempt count.
                logger.warning(
                    "OpenRouter structured output failed validation (attempt %d/%d): %s",
                    attempt,
                    _MAX_STRUCTURED_OUTPUT_ATTEMPTS,
                    type(exc).__name__,
                )
                last_error = exc
                messages = [
                    *messages,
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": "That response was not valid JSON matching the required "
                        "schema. Reply again with ONLY valid JSON matching the schema - "
                        "no extra text, no markdown code fences.",
                    },
                ]
                continue

        raise LLMInvalidResponseError(
            f"OpenRouter did not return a schema-valid response after "
            f"{_MAX_STRUCTURED_OUTPUT_ATTEMPTS} attempts."
        ) from last_error

    async def _create_completion(self, messages: list[dict], response_format: dict):
        """Translate the openai SDK's exception hierarchy into our
        provider-agnostic ones (app/ai/errors.py) - the only place in this
        class that touches openai.* exception types."""
        try:
            return await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format=response_format,
            )
        except openai.AuthenticationError as exc:
            raise LLMAuthenticationError(
                "OpenRouter authentication failed - check OPENROUTER_API_KEY."
            ) from exc
        except openai.RateLimitError as exc:
            raise LLMRateLimitError("OpenRouter rate limit exceeded.") from exc
        except openai.APITimeoutError as exc:
            raise LLMTimeoutError("OpenRouter request timed out.") from exc
        except openai.APIConnectionError as exc:
            raise LLMConnectionError("Could not connect to OpenRouter.") from exc
        except openai.APIStatusError as exc:
            # Covers 400/402/403/502/503/etc. Never echo the raw response
            # body - it can include the request content OpenRouter echoes
            # back on some error types.
            logger.warning("OpenRouter API error: status=%s", exc.status_code)
            raise LLMProviderError(f"OpenRouter API error (status {exc.status_code}).") from exc

    async def generate_question(
        self,
        *,
        topic: Topic,
        difficulty: Difficulty,
        previously_asked: list[str],
    ) -> GeneratedQuestion:
        prompt = build_question_prompt(
            topic=topic, difficulty=difficulty, previously_asked=previously_asked
        )
        return await self._complete_structured(prompt, GeneratedQuestion)

    async def evaluate_answer(
        self,
        *,
        question: str,
        topic: Topic,
        difficulty: Difficulty,
        answer_text: str,
    ) -> AnswerEvaluation:
        prompt = build_evaluation_prompt(
            question=question, topic=topic, difficulty=difficulty, answer_text=answer_text
        )
        return await self._complete_structured(prompt, AnswerEvaluation)

    async def generate_follow_up_question(
        self,
        *,
        original_question: str,
        original_answer: str,
        topic: Topic,
        difficulty: Difficulty,
        weaknesses: list[str],
        vague_flags: list[str],
    ) -> GeneratedQuestion:
        prompt = build_follow_up_prompt(
            original_question=original_question,
            original_answer=original_answer,
            topic=topic,
            difficulty=difficulty,
            weaknesses=weaknesses,
            vague_flags=vague_flags,
        )
        return await self._complete_structured(prompt, GeneratedQuestion)

    async def extract_candidate_profile(self, *, resume_text: str) -> CandidateProfile:
        prompt = build_resume_extraction_prompt(resume_text=resume_text)
        return await self._complete_structured(prompt, CandidateProfile)
