from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.engine.coach import Coach


@pytest.fixture
def coach() -> Coach:
    return Coach(MagicMock())


def _tool_call(name: str, arguments: str, call_id: str = "call_123") -> MagicMock:
    tool_call = MagicMock()
    tool_call.type = "function_call"
    tool_call.name = name
    tool_call.arguments = arguments
    tool_call.call_id = call_id
    return tool_call


def _response(output: list[MagicMock], text: str = "", response_id: str = "resp_1") -> MagicMock:
    response = MagicMock()
    response.output = output
    response.output_text = text
    response.id = response_id
    return response


def _stub_tool(coach: Coach, name: str, result: Any) -> Any:
    """Replace a tool in the registry the coach actually dispatches through."""
    return patch.dict(coach.TOOL_REGISTRY, {name: MagicMock(return_value=result)})


def test_every_tool_schema_is_registered_and_strict(coach: Coach) -> None:
    names = [tool["name"] for tool in coach.TOOLS]
    assert set(names) == set(coach.TOOL_REGISTRY)

    for tool in coach.TOOLS:
        if not tool.get("strict"):
            continue
        parameters = tool["parameters"]
        assert parameters["additionalProperties"] is False
        assert set(parameters["required"]) == set(parameters["properties"])


def test_ask_coach_returns_structured_response(coach: Coach) -> None:
    response = _response([], "Your squat e1RM is trending up.")

    with patch.object(coach.client.responses, "create", return_value=response):
        result = coach.ask_coach("How is my squat trending?")

    assert result == {
        "answer": "Your squat e1RM is trending up.",
        "used_tools": [],
        "citations": [],
    }


def test_ask_coach_tracks_used_tools(coach: Coach) -> None:
    tool_call = _tool_call("query_workouts", '{"metric": "tonnage", "exercise": "Back Squat"}')
    first_response = _response([tool_call])
    second_response = _response([], "You lifted 10,000 kg this week.", response_id="resp_2")

    with (
        patch.object(
            coach.client.responses, "create", side_effect=[first_response, second_response]
        ),
        _stub_tool(coach, "query_workouts", {"metric": "tonnage", "result": []}),
    ):
        result = coach.ask_coach("How much did I squat this week?")

    assert result["answer"] == "You lifted 10,000 kg this week."
    assert result["used_tools"] == ["query_workouts"]
    assert result["citations"] == []


def test_ask_coach_cites_every_retrieved_passage(coach: Coach) -> None:
    tool_call = _tool_call("search_coaching_docs", '{"query": "should I deload?", "k": null}')
    first_response = _response([tool_call])
    second_response = _response([], "A deload is reasonable.", response_id="resp_2")
    passages = {
        "status": "ok",
        "results": [
            {
                "document_id": 1,
                "document": "Deload Guidelines",
                "chunk_index": 2,
                "content": "Deload every four to six weeks.",
            },
            {
                "document_id": 2,
                "document": "RPE and Autoregulation",
                "chunk_index": 0,
                "content": "Use RPE to autoregulate.",
            },
        ],
    }

    with (
        patch.object(
            coach.client.responses, "create", side_effect=[first_response, second_response]
        ),
        _stub_tool(coach, "search_coaching_docs", passages),
    ):
        result = coach.ask_coach("Should I deload?")

    assert result["used_tools"] == ["search_coaching_docs"]
    assert result["citations"] == [
        {"document_id": 1, "document": "Deload Guidelines", "chunk_index": 2},
        {"document_id": 2, "document": "RPE and Autoregulation", "chunk_index": 0},
    ]


def test_ask_coach_deduplicates_repeated_passages_across_searches(coach: Coach) -> None:
    passage = {
        "document_id": 1,
        "document": "Deload Guidelines",
        "chunk_index": 2,
        "content": "Deload every four to six weeks.",
    }
    first_call = _tool_call("search_coaching_docs", '{"query": "deload", "k": 5}', "call_1")
    second_call = _tool_call("search_coaching_docs", '{"query": "deloading", "k": 5}', "call_2")
    responses = [
        _response([first_call]),
        _response([second_call], response_id="resp_2"),
        _response([], "A deload is reasonable.", response_id="resp_3"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses),
        _stub_tool(coach, "search_coaching_docs", {"status": "ok", "results": [passage]}),
    ):
        result = coach.ask_coach("Should I deload?")

    assert result["citations"] == [
        {"document_id": 1, "document": "Deload Guidelines", "chunk_index": 2}
    ]


def test_ask_coach_reports_no_citations_when_nothing_matches(coach: Coach) -> None:
    tool_call = _tool_call("search_coaching_docs", '{"query": "marathon", "k": null}')
    responses = [
        _response([tool_call]),
        _response([], "I don't have material on marathon training.", response_id="resp_2"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses),
        _stub_tool(coach, "search_coaching_docs", {"status": "no_match", "results": []}),
    ):
        result = coach.ask_coach("How should I train for a marathon?")

    assert result["used_tools"] == ["search_coaching_docs"]
    assert result["citations"] == []
