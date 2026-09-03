"""
Explicit interview state machine (spec section 20).

Deliberately pure/deterministic and separate from the AI-calling code in
engine.py, so state transitions can be unit tested without a database or an
LLM. The API/engine layer is the only thing allowed to call `transition()`;
nothing should mutate an interview's status field directly.
"""

from app.schemas.interview import InterviewState

# Map of "from state" -> set of states it may legally move to.
_ALLOWED_TRANSITIONS: dict[InterviewState, set[InterviewState]] = {
    InterviewState.SETUP: {InterviewState.QUESTIONING, InterviewState.CANCELLED},
    InterviewState.QUESTIONING: {
        InterviewState.EVALUATING,
        InterviewState.CANCELLED,
    },
    InterviewState.EVALUATING: {
        InterviewState.NEXT_QUESTION,
        InterviewState.COMPLETED,
        InterviewState.CANCELLED,
    },
    InterviewState.NEXT_QUESTION: {
        InterviewState.QUESTIONING,
        InterviewState.CANCELLED,
    },
    # Reserved for later milestones - no code transitions into these yet.
    InterviewState.LISTENING: {
        InterviewState.EVALUATING,
        InterviewState.CANCELLED,
    },
    InterviewState.FOLLOW_UP: {
        InterviewState.EVALUATING,
        InterviewState.CANCELLED,
    },
    InterviewState.COMPLETED: set(),
    InterviewState.CANCELLED: set(),
}


class InvalidTransitionError(ValueError):
    def __init__(self, current: InterviewState, target: InterviewState):
        super().__init__(f"Cannot transition from {current} to {target}")
        self.current = current
        self.target = target


def transition(current: InterviewState, target: InterviewState) -> InterviewState:
    """Validate and return the new state, or raise InvalidTransitionError."""
    if target not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidTransitionError(current, target)
    return target


def is_terminal(state: InterviewState) -> bool:
    return state in (InterviewState.COMPLETED, InterviewState.CANCELLED)
