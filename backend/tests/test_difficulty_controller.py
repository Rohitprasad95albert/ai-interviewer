from app.interview.difficulty_controller import next_difficulty
from app.schemas.interview import AnswerEvaluation

BASE_SCORES = dict(
    technical_accuracy=5,
    depth=5,
    completeness=5,
    clarity=5,
    relevance=5,
    communication=5,
)


def evaluation_with_overall(overall: float) -> AnswerEvaluation:
    return AnswerEvaluation(**BASE_SCORES, overall=overall)


def test_strong_answer_raises_difficulty():
    assert next_difficulty("easy", evaluation_with_overall(9)) == "medium"
    assert next_difficulty("medium", evaluation_with_overall(9)) == "hard"


def test_weak_answer_lowers_difficulty():
    assert next_difficulty("hard", evaluation_with_overall(2)) == "medium"
    assert next_difficulty("medium", evaluation_with_overall(2)) == "easy"


def test_mediocre_answer_holds_steady():
    assert next_difficulty("medium", evaluation_with_overall(6)) == "medium"


def test_difficulty_cannot_go_above_hard_or_below_easy():
    assert next_difficulty("hard", evaluation_with_overall(10)) == "hard"
    assert next_difficulty("easy", evaluation_with_overall(0)) == "easy"


def test_moves_at_most_one_step_even_on_extreme_scores():
    # A single perfect answer on "easy" should land on "medium", not jump
    # straight to "hard" - spec section 8 wants gradual adaptation.
    assert next_difficulty("easy", evaluation_with_overall(10)) == "medium"
