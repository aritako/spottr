from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app
from app.shared.schemas.coach import AskResponse


def _client_with_mock_db() -> TestClient:
    app.dependency_overrides[get_db] = lambda: iter([MagicMock()])
    return TestClient(app)


def test_ask_coach_endpoint() -> None:
    expected = AskResponse(
        answer="Your squat e1RM is trending up.",
        used_tools=["query_workouts"],
        citations=[],
    )

    client = _client_with_mock_db()
    try:
        with patch(
            "app.api.controllers.coach.CoachHandler.ask",
            return_value=expected,
        ):
            response = client.post("/coach/ask", json={"question": "How is my squat trending?"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Your squat e1RM is trending up.",
        "used_tools": ["query_workouts"],
        "citations": [],
    }


def test_ask_coach_endpoint_validation_error() -> None:
    client = _client_with_mock_db()
    try:
        response = client.post("/coach/ask", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
