"""
Deterministic difficulty controller (spec section 8: Adaptive Interview
Engine).

Deliberately does NOT just trust the LLM evaluation's own
`suggested_next_difficulty` field as the control signal - spec section 23
is explicit that deterministic application logic, not the LLM, should own
state transitions. The LLM's suggestion is still stored on the evaluation
for transparency/debugging, but the actual difficulty step is computed here
from the numeric `overall` score, and is capped at one step per answer so a
single unusually good or bad answer can't swing difficulty from easy to
hard in one move.
"""

from app.schemas.interview import AnswerEvaluation, Difficulty

_ORDER: list[Difficulty] = ["easy", "medium", "hard"]

# Thresholds are intentionally not at the extremes (0/10) - a 7/10 is a
# solid answer and should be rewarded with a harder question next, not
# require a near-perfect score.
_RAISE_THRESHOLD = 8.0
_LOWER_THRESHOLD = 4.0


def _step(current: Difficulty, direction: int) -> Difficulty:
    index = _ORDER.index(current)
    new_index = max(0, min(len(_ORDER) - 1, index + direction))
    return _ORDER[new_index]


def next_difficulty(current: Difficulty, evaluation: AnswerEvaluation) -> Difficulty:
    """One step up if the answer was strong, one step down if it was weak,
    otherwise hold steady. Never moves more than one level per answer."""
    if evaluation.overall >= _RAISE_THRESHOLD:
        return _step(current, +1)
    if evaluation.overall <= _LOWER_THRESHOLD:
        return _step(current, -1)
    return current
