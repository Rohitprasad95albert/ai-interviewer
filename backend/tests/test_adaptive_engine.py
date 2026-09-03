"""
Integration tests for the Milestone 5 adaptive behavior, driven through the
real API against a real (test) MongoDB, using the StubLLMClient - same
pattern as test_interview_flow.py. Pure-logic pieces (difficulty stepping,
weak-topic detection, topic selection) have their own fast unit tests in
test_difficulty_controller.py, test_weakness_tracker.py, and
test_topic_selection.py; these tests exist to prove the engine actually
wires those pieces together correctly through the real request/response
cycle.
"""

from fastapi.testclient import TestClient

from app.main import app

VAGUE_ANSWER = "Because it is scalable."

STRONG_ANSWER = (
    "A stack is LIFO - the last element pushed is the first popped, which "
    "is exactly why undo/redo history in editors uses one: undoing means "
    "popping the most recent action off the top. A queue is FIFO - first "
    "in, first out - which matches task scheduling or a print queue, where "
    "fairness means whoever arrived first gets served first, not whoever "
    "arrived most recently."
)


def test_vague_answer_produces_a_follow_up_question_on_the_same_topic():
    with TestClient(app) as client:
        interview = client.post(
            "/api/interviews",
            json={"topics": ["dsa"], "difficulty": "medium", "question_count": 4},
        ).json()

        result = client.post(
            f"/api/interviews/{interview['id']}/answer", json={"answer_text": VAGUE_ANSWER}
        ).json()

        assert result["interview"]["status"] == "follow_up"
        follow_up_question = result["interview"]["current_question"]
        assert follow_up_question["is_follow_up"] is True
        assert follow_up_question["topic"] == "dsa"
        assert follow_up_question["index"] == 1


def test_follow_ups_cap_at_one_in_a_row():
    with TestClient(app) as client:
        interview = client.post(
            "/api/interviews",
            json={"topics": ["dsa"], "difficulty": "medium", "question_count": 4},
        ).json()

        first = client.post(
            f"/api/interviews/{interview['id']}/answer", json={"answer_text": VAGUE_ANSWER}
        ).json()
        assert first["interview"]["status"] == "follow_up"

        # Answer the follow-up vaguely too - a second consecutive follow-up
        # should be refused by the cap, forcing a move to the next topic
        # question instead.
        second = client.post(
            f"/api/interviews/{interview['id']}/answer", json={"answer_text": VAGUE_ANSWER}
        ).json()
        assert second["interview"]["status"] == "questioning"
        assert second["interview"]["current_question"]["is_follow_up"] is False
        assert second["interview"]["current_question_index"] == 2


def test_strong_answer_raises_difficulty_for_the_next_question():
    with TestClient(app) as client:
        interview = client.post(
            "/api/interviews",
            json={"topics": ["dsa", "oop"], "difficulty": "easy", "question_count": 3},
        ).json()
        assert interview["current_difficulty"] == "easy"

        result = client.post(
            f"/api/interviews/{interview['id']}/answer", json={"answer_text": STRONG_ANSWER}
        ).json()

        assert result["evaluation"]["scores"]["overall"] >= 8
        assert result["interview"]["current_difficulty"] == "medium"
        assert result["interview"]["current_question"]["difficulty"] == "medium"


def test_report_reflects_follow_up_questions():
    with TestClient(app) as client:
        interview = client.post(
            "/api/interviews",
            json={"topics": ["dsa"], "difficulty": "medium", "question_count": 3},
        ).json()

        client.post(f"/api/interviews/{interview['id']}/answer", json={"answer_text": VAGUE_ANSWER})
        client.post(f"/api/interviews/{interview['id']}/answer", json={"answer_text": STRONG_ANSWER})
        client.post(f"/api/interviews/{interview['id']}/answer", json={"answer_text": STRONG_ANSWER})

        report = client.get(f"/api/interviews/{interview['id']}/report").json()
        assert report["interview"]["status"] == "completed"
        assert len(report["questions"]) == 3
        assert any(q["is_follow_up"] for q in report["questions"])
