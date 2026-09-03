"""
Deterministic vague-answer detection (spec section 12).

Runs independently of whichever LLM client is active - a candidate saying
"because it's scalable" with no elaboration is detectable with a phrase
match, and we'd rather catch it reliably than hope the evaluator model
notices. This produces `vague_flags` that are attached to the evaluation
and can drive a future "challenge this claim" follow-up (Milestone 5).
"""

import re

# Buzzword-as-justification phrases the spec explicitly calls out. Matched
# case-insensitively; `\b` boundaries avoid false positives like "faster"
# inside a longer, more specific word.
_VAGUE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bbecause it('?s| is) faster\b",
        r"\bbecause it('?s| is) scalable\b",
        r"\bbecause it('?s| is) secure\b",
        r"\bit optimizes performance\b",
        r"\bit uses ai\b",
        r"\bit handles large data\b",
    ]
]

# A short, unelaborated answer is a weaker but still useful signal.
_MIN_SUBSTANTIVE_LENGTH = 40


def detect_vague_flags(answer_text: str) -> list[str]:
    """Return a list of human-readable flags describing vagueness found."""
    flags: list[str] = []

    for pattern in _VAGUE_PATTERNS:
        match = pattern.search(answer_text)
        if match:
            flags.append(f'Unexplained buzzword justification: "{match.group(0)}"')

    stripped = answer_text.strip()
    if stripped and len(stripped) < _MIN_SUBSTANTIVE_LENGTH:
        flags.append("Answer is very short - likely missing explanation or depth")

    return flags
