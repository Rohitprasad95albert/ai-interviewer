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
        """
        A deep-dive challenge on the candidate's own previous answer (spec
        section 9: "Why?/How?/trade-offs"), not a fresh topic question.
        """
        ...
