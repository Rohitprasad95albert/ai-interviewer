"""
Real LLM client backed by the Anthropic Messages API (anthropic Python SDK
1.x). Implements the same `LLMClient` protocol as StubLLMClient - the
interview engine never imports this module directly (see app/ai/factory.py).

Uses `client.messages.parse(..., output_format=<PydanticModel>)`, which
validates the response against the schema and returns `.parsed_output` as an
already-validated instance - the current recommended structured-output
pattern (see the Anthropic Python SDK docs). We never trust raw model text
as JSON without going through this.

NOTE: this class is written against the documented SDK API but has not been
exercised against a live key in this environment - it's implemented,
type-checked, but not yet verified end-to-end. Verify with a real key before
relying on it (see README "Known limitations").
"""

import logging

import anthropic

from app.ai.prompt_builder import build_evaluation_prompt, build_question_prompt
from app.core.config import settings
from app.schemas.interview import AnswerEvaluation, Difficulty, GeneratedQuestion, Topic

logger = logging.getLogger(__name__)


class AnthropicLLMClient:
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

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
        response = await self._client.messages.parse(
            model=settings.anthropic_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            output_format=GeneratedQuestion,
        )
        return response.parsed_output

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
        response = await self._client.messages.parse(
            model=settings.anthropic_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
            output_format=AnswerEvaluation,
        )
        return response.parsed_output
