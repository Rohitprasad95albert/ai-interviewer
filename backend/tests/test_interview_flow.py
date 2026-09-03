"""
Integration test: drives the real API (create -> answer -> answer ->
completed -> report) against the real local MongoDB (see conftest.py for the
separate test database) using the StubLLMClient (no ANTHROPIC_API_KEY is set
in this environment, so the app falls back to it automatically).
"""

from fastapi.testclient import TestClient

from app.main import app

GOOD_ANSWER = (
    "A stack is LIFO - the last element pushed is the first popped, useful "
    "for undo history. A queue is FIFO - first in, first out - useful for "
    "task scheduling where order of arrival matters."
)


def test_full_interview_completes_and_produces_a_report():
    with TestClient(app) as client:
        create_response = client.post(
            "/api/interviews",
            json={"topics": ["dsa"], "difficulty": "easy", "question_count": 2},
        )
        assert create_response.status_code == 201
        interview = create_response.json()
        assert interview["status"] == "questioning"
        assert interview["current_question"] is not None
        assert interview["current_question"]["index"] == 0
        interview_id = interview["id"]

        first = client.post(
            f"/api/interviews/{interview_id}/answer", json={"answer_text": GOOD_ANSWER}
        )
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["evaluation"]["scores"]["overall"] >= 0
        assert first_body["interview"]["status"] == "questioning"
        assert first_body["interview"]["current_question_index"] == 1

        second = client.post(
            f"/api/interviews/{interview_id}/answer", json={"answer_text": GOOD_ANSWER}
        )
        assert second.status_code == 200
        second_body = second.json()
        assert second_body["interview"]["status"] == "completed"
        assert second_body["interview"]["current_question"] is None

        report = client.get(f"/api/interviews/{interview_id}/report")
        assert report.status_code == 200
        report_body = report.json()
        assert len(report_body["questions"]) == 2
        assert len(report_body["evaluations"]) == 2
        assert report_body["average_overall"] > 0


def test_vague_answer_is_flagged_and_scored_lower_than_a_good_one():
    with TestClient(app) as client:
        interview = client.post(
            "/api/interviews",
            json={"topics": ["dbms"], "difficulty": "medium", "question_count": 1},
        ).json()

        answer = client.post(
            f"/api/interviews/{interview['id']}/answer",
            json={"answer_text": "Because it is scalable."},
        )
        body = answer.json()
        assert body["evaluation"]["vague_flags"]  # non-empty
        assert body["evaluation"]["scores"]["overall"] < 8


def test_submitting_an_answer_to_a_completed_interview_is_rejected():
    with TestClient(app) as client:
        interview = client.post(
            "/api/interviews",
            json={"topics": ["oop"], "difficulty": "easy", "question_count": 1},
        ).json()
        client.post(
            f"/api/interviews/{interview['id']}/answer", json={"answer_text": GOOD_ANSWER}
        )

        second_attempt = client.post(
            f"/api/interviews/{interview['id']}/answer", json={"answer_text": GOOD_ANSWER}
        )
        assert second_attempt.status_code == 409


def test_unknown_interview_id_returns_404():
    with TestClient(app) as client:
        response = client.get("/api/interviews/000000000000000000000000")
        assert response.status_code == 404


def test_malformed_interview_id_returns_404_not_500():
    with TestClient(app) as client:
        response = client.get("/api/interviews/not-a-valid-object-id")
        assert response.status_code == 404


def test_create_interview_rejects_empty_topics():
    with TestClient(app) as client:
        response = client.post(
            "/api/interviews", json={"topics": [], "question_count": 3}
        )
        assert response.status_code == 422
