from app.interview.weakness_tracker import compute_weak_topics


def _eval(topic: str, overall: float) -> dict:
    return {"topic": topic, "scores": {"overall": overall}}


def test_no_topics_flagged_with_fewer_than_two_observations():
    # Spec section 15: "Do not overreact to a single bad answer."
    evaluations = [_eval("os", 1.0)]
    assert compute_weak_topics(evaluations) == set()


def test_topic_flagged_after_two_low_scores():
    evaluations = [_eval("os", 3.0), _eval("os", 2.0)]
    assert compute_weak_topics(evaluations) == {"os"}


def test_topic_not_flagged_if_average_is_at_or_above_threshold():
    evaluations = [_eval("dbms", 5.0), _eval("dbms", 6.0)]
    assert compute_weak_topics(evaluations) == set()


def test_only_the_weak_topic_is_flagged_among_several():
    evaluations = [
        _eval("os", 2.0),
        _eval("os", 3.0),
        _eval("dsa", 9.0),
        _eval("dsa", 8.0),
    ]
    assert compute_weak_topics(evaluations) == {"os"}


def test_one_low_and_one_high_score_on_same_topic_averages_out():
    evaluations = [_eval("cn", 1.0), _eval("cn", 9.0)]
    assert compute_weak_topics(evaluations) == set()
