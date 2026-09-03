"""
Session-level weak-topic detection (spec section 8's "weak concept detected
-> targeted question" branch). This is deliberately scoped to the CURRENT
interview only - detecting weaknesses that recur ACROSS interviews is a
separate, larger feature (spec section 15, Milestone 6) that needs
historical data this milestone doesn't build yet. Conflating the two would
either make this trigger on noise (one bad answer) or require the
cross-session infrastructure before it's ready.

Requires at least MIN_OBSERVATIONS answers on a topic before calling it
"weak" - spec section 15: "Do not overreact to a single bad answer."
"""

from collections import defaultdict

MIN_OBSERVATIONS = 2
WEAK_AVERAGE_THRESHOLD = 5.0


def compute_weak_topics(evaluation_docs: list[dict]) -> set[str]:
    """
    evaluation_docs: the raw dicts from repository.list_evaluations (each
    has "topic" and "scores": {"overall": float, ...}).
    """
    scores_by_topic: dict[str, list[float]] = defaultdict(list)
    for doc in evaluation_docs:
        scores_by_topic[doc["topic"]].append(doc["scores"]["overall"])

    weak_topics = set()
    for topic, scores in scores_by_topic.items():
        if len(scores) >= MIN_OBSERVATIONS and (sum(scores) / len(scores)) < WEAK_AVERAGE_THRESHOLD:
            weak_topics.add(topic)
    return weak_topics
