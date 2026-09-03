"""Fills the versioned prompt templates with per-call context."""

from app.ai.prompts import load_prompt
from app.schemas.interview import Difficulty, Topic


def build_question_prompt(
    *, topic: Topic, difficulty: Difficulty, previously_asked: list[str]
) -> str:
    template = load_prompt("interviewer", "technical_v1.txt")
    asked = "\n".join(f"- {q}" for q in previously_asked) or "(none yet)"
    return template.format(topic=topic, difficulty=difficulty, previously_asked=asked)


def build_evaluation_prompt(
    *, question: str, topic: Topic, difficulty: Difficulty, answer_text: str
) -> str:
    template = load_prompt("evaluator", "technical_v1.txt")
    return template.format(
        topic=topic, difficulty=difficulty, question=question, answer_text=answer_text
    )
