import pytest

from app.interview.state_machine import InvalidTransitionError, is_terminal, transition
from app.schemas.interview import InterviewState


def test_setup_can_move_to_questioning():
    assert transition(InterviewState.SETUP, InterviewState.QUESTIONING) == InterviewState.QUESTIONING


def test_full_happy_path_sequence():
    state = InterviewState.SETUP
    for target in [
        InterviewState.QUESTIONING,
        InterviewState.EVALUATING,
        InterviewState.NEXT_QUESTION,
        InterviewState.QUESTIONING,
        InterviewState.EVALUATING,
        InterviewState.COMPLETED,
    ]:
        state = transition(state, target)
    assert state == InterviewState.COMPLETED


def test_cannot_skip_questioning_from_setup():
    with pytest.raises(InvalidTransitionError):
        transition(InterviewState.SETUP, InterviewState.EVALUATING)


def test_cannot_leave_a_terminal_state():
    with pytest.raises(InvalidTransitionError):
        transition(InterviewState.COMPLETED, InterviewState.QUESTIONING)


def test_can_cancel_from_any_active_state():
    for state in [InterviewState.SETUP, InterviewState.QUESTIONING, InterviewState.EVALUATING]:
        assert transition(state, InterviewState.CANCELLED) == InterviewState.CANCELLED


def test_is_terminal():
    assert is_terminal(InterviewState.COMPLETED)
    assert is_terminal(InterviewState.CANCELLED)
    assert not is_terminal(InterviewState.QUESTIONING)
