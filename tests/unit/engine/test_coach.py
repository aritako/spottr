from unittest.mock import MagicMock, patch

import pytest

from app.engine.coach import Coach


@pytest.fixture
def coach() -> Coach:
    return Coach(MagicMock())


def test_ask_coach_returns_structured_response(coach: Coach) -> None:
    response = MagicMock()
    response.output = []
    response.output_text = "Your squat e1RM is trending up."

    with patch.object(coach.client.responses, "create", return_value=response):
        result = coach.ask_coach("How is my squat trending?")

    assert result == {
        "answer": "Your squat e1RM is trending up.",
        "used_tools": [],
        "citations": [],
    }


def test_ask_coach_tracks_used_tools(coach: Coach) -> None:
    tool_call = MagicMock()
    tool_call.type = "function_call"
    tool_call.name = "query_workouts"
    tool_call.arguments = '{"metric": "tonnage", "exercise": "Back Squat"}'
    tool_call.call_id = "call_123"

    first_response = MagicMock()
    first_response.output = [tool_call]
    first_response.id = "resp_1"
    first_response.output_text = ""

    second_response = MagicMock()
    second_response.output = []
    second_response.output_text = "You lifted 10,000 kg this week."

    with patch.object(
        coach.client.responses, "create", side_effect=[first_response, second_response]
    ):
        with patch.object(
            coach.tools, "query_workouts", return_value={"metric": "tonnage", "result": []}
        ):
            result = coach.ask_coach("How much did I squat this week?")

    assert result["answer"] == "You lifted 10,000 kg this week."
    assert result["used_tools"] == ["query_workouts"]
    assert result["citations"] == []
