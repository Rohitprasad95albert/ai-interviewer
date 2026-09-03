from app.interview.engine import select_next_topic


def test_rotates_normally_with_no_weak_topics():
    topics = ["dsa", "oop"]
    assert select_next_topic(topics, 0, weak_topics=set()) == "dsa"
    assert select_next_topic(topics, 1, weak_topics=set()) == "oop"
    assert select_next_topic(topics, 2, weak_topics=set()) == "dsa"


def test_weak_topic_overrides_rotation():
    topics = ["dsa", "oop"]
    # Rotation would pick "dsa" for index 0, but "oop" has emerged weak -
    # the targeted-question override should win.
    assert select_next_topic(topics, 0, weak_topics={"oop"}) == "oop"


def test_weak_topic_outside_this_interviews_selection_is_ignored():
    # A topic can only be "weak" for targeting purposes if it's actually
    # one of the topics selected for this interview.
    topics = ["dsa", "oop"]
    assert select_next_topic(topics, 0, weak_topics={"os"}) == "dsa"


def test_multiple_weak_topics_picks_deterministically():
    topics = ["dsa", "oop", "dbms"]
    result = select_next_topic(topics, 0, weak_topics={"oop", "dbms"})
    assert result in {"oop", "dbms"}
    # Same inputs -> same output (alphabetical tiebreak), not random.
    assert result == select_next_topic(topics, 0, weak_topics={"oop", "dbms"})
