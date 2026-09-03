"""
The interview engine talks to this interface, never to a concrete SDK. Swap
StubLLMClient for AnthropicLLMClient (app/core/config.py picks one based on
whether ANTHROPIC_API_KEY is set) without touching engine.py or the API
routes - see spec section 23 (AI Architecture: separate responsibilities).
"""

from typing import Protocol

from app.schemas.interview import AnswerEvaluation, Difficulty, GeneratedQuestion, Topic


class LLMClient(Protocol):
    async def generate_question(
        self,
        *,
        topic: Topic,
        difficulty: Difficulty,
        previously_asked: list[str],
    ) -> GeneratedQuestion: ...

    async def evaluate_answer(
        self,
        *,
        question: str,
        topic: Topic,
        difficulty: Difficulty,
        answer_text: str,
    ) -> AnswerEvaluation: ...
