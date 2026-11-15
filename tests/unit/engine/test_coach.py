import json
import logging
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.engine.coach import Coach
from app.engine.prompts.retry import SCOPE_RETRY
from app.engine.rejections import COULD_NOT_COMPLETE, NOTHING_FOUND, OUT_OF_SCOPE

PASSAGE = {
    "document_id": 1,
    "document_title": "Deload Guidelines",
    "chunk_index": 2,
    "content": "Deload every four to six weeks.",
}

CITATION = {
    "document_id": 1,
    "document_title": "Deload Guidelines",
    "chunk_index": 2,
}


@pytest.fixture
def coach() -> Coach:
    return Coach(MagicMock())


@pytest.fixture
def engine_logs(caplog: pytest.LogCaptureFixture) -> Iterator[pytest.LogCaptureFixture]:
    """Capture engine logs even after Alembic's logging setup disables the logger."""
    engine_logger = logging.getLogger("app.engine.coach")
    was_disabled = engine_logger.disabled
    engine_logger.disabled = False
    caplog.set_level(logging.WARNING, logger="app.engine.coach")
    try:
        yield caplog
    finally:
        engine_logger.disabled = was_disabled


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


@contextmanager
def _stub_search(coach: Coach, result: Any) -> Iterator[MagicMock]:
    """Replace both dispatch paths the docs tool can take."""
    mock = MagicMock(return_value=result)
    with (
        patch.object(coach.tools, "search_coaching_docs", mock),
        patch.dict(coach.TOOL_REGISTRY, {"search_coaching_docs": mock}),
    ):
        yield mock


def _stub_result(coach: Coach, tool: str, result: Any) -> AbstractContextManager[Any]:
    """Stub a tool result through the path the coach actually dispatches it."""
    if tool == "search_coaching_docs":
        return _stub_search(coach, result)
    return _stub_tool(coach, tool, result)


def test_every_tool_schema_is_registered_and_strict(coach: Coach) -> None:
    names = [tool["name"] for tool in coach.TOOLS]
    assert set(names) == set(coach.TOOL_REGISTRY)

    for tool in coach.TOOLS:
        if not tool.get("strict"):
            continue
        parameters = tool["parameters"]
        assert parameters["additionalProperties"] is False
        assert set(parameters["required"]) == set(parameters["properties"])


def test_search_coaching_docs_schema_has_no_query_parameter(coach: Coach) -> None:
    tool = next(tool for tool in coach.TOOLS if tool["name"] == "search_coaching_docs")

    assert "query" not in tool["parameters"]["properties"]
    assert tool["parameters"]["required"] == ["k"]


def test_ask_coach_sends_one_chained_correction_turn_for_a_no_tool_answer(
    coach: Coach, engine_logs: pytest.LogCaptureFixture
) -> None:
    question = "Hey! Ready to train?"
    responses = [
        _response([], "Hey! What are we working on?", response_id="resp_1"),
        _response(
            [_tool_call("search_coaching_docs", '{"k": null}', "call_search")],
            response_id="resp_2",
        ),
        _response([], "Deload every four to six weeks.", response_id="resp_3"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        _stub_search(coach, {"status": "ok", "passages": [PASSAGE]}),
    ):
        result = coach.ask_coach(question)

    assert result == {
        "answer": "Deload every four to six weeks.",
        "used_tools": ["search_coaching_docs"],
        "citations": [CITATION],
    }
    assert create.call_count == 3

    retry = create.call_args_list[1].kwargs
    assert retry["previous_response_id"] == "resp_1"
    assert retry["instructions"] == create.call_args_list[0].kwargs["instructions"]
    assert retry["tools"] == coach.TOOLS
    assert isinstance(retry["input"], str)
    assert retry["input"] == SCOPE_RETRY
    assert "without calling any tool" in retry["input"]
    assert question not in retry["input"]

    assert "retried" in engine_logs.text
    assert "no substantive tool call" in engine_logs.text
    assert "search_coaching_docs" in engine_logs.text
    assert question not in engine_logs.text


def test_ask_coach_returns_the_out_of_scope_rejection_after_a_second_no_tool_answer(
    coach: Coach, engine_logs: pytest.LogCaptureFixture
) -> None:
    question = "What is a good banana bread recipe?"
    responses = [
        _response([], "Here is a recipe.", response_id="resp_1"),
        _response([], "Use very ripe bananas.", response_id="resp_2"),
    ]

    with patch.object(coach.client.responses, "create", side_effect=responses) as create:
        result = coach.ask_coach(question)

    assert result == {
        "answer": OUT_OF_SCOPE,
        "used_tools": [],
        "citations": [],
    }
    assert create.call_count == 2
    assert "retried" in engine_logs.text
    assert "blocked" in engine_logs.text
    assert "out-of-scope" in engine_logs.text
    assert "query_workouts" in engine_logs.text
    assert question not in engine_logs.text


def test_ask_coach_normalizes_an_all_empty_correction_turn_to_nothing_found(
    coach: Coach, engine_logs: pytest.LogCaptureFixture
) -> None:
    responses = [
        _response([], "You are getting stronger.", response_id="resp_1"),
        _response(
            [_tool_call("query_workouts", '{"metric": "tonnage"}', "call_workouts")],
            response_id="resp_2",
        ),
        _response([], "You lifted 12,400 kg.", response_id="resp_3"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        _stub_tool(coach, "query_workouts", {"result": "No matching workout data found."}),
    ):
        result = coach.ask_coach("How much did I lift?")

    assert result == {
        "answer": NOTHING_FOUND,
        "used_tools": ["query_workouts"],
        "citations": [],
    }
    assert create.call_count == 3
    assert [call.kwargs["input"] for call in create.call_args_list].count(SCOPE_RETRY) == 1
    assert "nothing-found" in engine_logs.text
    assert "query_workouts" in engine_logs.text
    assert "12,400" not in engine_logs.text


def test_ask_coach_returns_could_not_complete_when_the_retry_budget_is_spent(
    coach: Coach, engine_logs: pytest.LogCaptureFixture
) -> None:
    responses = [_response([], "You are getting stronger.", response_id="resp_1")]

    with patch.object(coach.client.responses, "create", side_effect=responses) as create:
        result = coach.ask_coach("How much did I lift?", max_iterations=1)

    assert result == {
        "answer": COULD_NOT_COMPLETE,
        "used_tools": [],
        "citations": [],
    }
    assert create.call_count == 1
    assert "blocked" in engine_logs.text
    assert "iteration budget" in engine_logs.text
    assert "query_workouts" in engine_logs.text


def test_ask_coach_returns_could_not_complete_when_the_last_iteration_finds_the_violation(
    coach: Coach, engine_logs: pytest.LogCaptureFixture
) -> None:
    unknown_call = _tool_call("query_nutrition", "{}", "call_unknown")
    responses = [
        _response([unknown_call], response_id="resp_1"),
        _response([], "I can answer without tools.", response_id="resp_2"),
    ]

    with patch.object(coach.client.responses, "create", side_effect=responses) as create:
        result = coach.ask_coach("How much did I lift?", max_iterations=2)

    assert result == {
        "answer": COULD_NOT_COMPLETE,
        "used_tools": [],
        "citations": [],
    }
    assert create.call_count == 2
    assert "blocked" in engine_logs.text
    assert "iteration budget" in engine_logs.text


def test_ask_coach_accumulates_tools_across_the_correction_turn(coach: Coach) -> None:
    unknown_call = _tool_call("query_nutrition", "{}", "call_unknown")
    responses = [
        _response([unknown_call], response_id="resp_1"),
        _response([], "I can answer without tools.", response_id="resp_2"),
        _response(
            [_tool_call("query_workouts", '{"metric": "tonnage"}', "call_workouts")],
            response_id="resp_3",
        ),
        _response([], "You lifted 10,000 kg this week.", response_id="resp_4"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        _stub_tool(
            coach,
            "query_workouts",
            {
                "metric": "tonnage",
                "group_by": "week",
                "result": [["Week of Jun 15, 2026", 10000.0]],
            },
        ),
    ):
        result = coach.ask_coach("How much did I squat this week?")

    assert result == {
        "answer": "You lifted 10,000 kg this week.",
        "used_tools": ["query_workouts"],
        "citations": [],
    }

    retry = create.call_args_list[2].kwargs
    assert retry["previous_response_id"] == "resp_2"
    assert retry["instructions"] == create.call_args_list[0].kwargs["instructions"]
    assert retry["tools"] == coach.TOOLS
    assert retry["input"] == SCOPE_RETRY


def test_ask_coach_tracks_used_tools(coach: Coach) -> None:
    tool_call = _tool_call("query_workouts", '{"metric": "tonnage", "exercise": "Back Squat"}')
    first_response = _response([tool_call])
    second_response = _response([], "You lifted 10,000 kg this week.", response_id="resp_2")

    with (
        patch.object(
            coach.client.responses, "create", side_effect=[first_response, second_response]
        ),
        _stub_tool(
            coach,
            "query_workouts",
            {
                "metric": "tonnage",
                "group_by": "week",
                "result": [["Week of Jun 15, 2026", 10000.0]],
            },
        ),
    ):
        result = coach.ask_coach("How much did I squat this week?")

    assert result["answer"] == "You lifted 10,000 kg this week."
    assert result["used_tools"] == ["query_workouts"]
    assert result["citations"] == []


def test_ask_coach_cites_every_retrieved_passage(coach: Coach) -> None:
    tool_call = _tool_call("search_coaching_docs", '{"k": null}')
    first_response = _response([tool_call])
    second_response = _response([], "A deload is reasonable.", response_id="resp_2")
    passages = {
        "status": "ok",
        "passages": [
            {
                "document_id": 1,
                "document_title": "Deload Guidelines",
                "chunk_index": 2,
                "content": "Deload every four to six weeks.",
            },
            {
                "document_id": 2,
                "document_title": "RPE and Autoregulation",
                "chunk_index": 0,
                "content": "Use RPE to autoregulate.",
            },
        ],
    }

    with (
        patch.object(
            coach.client.responses, "create", side_effect=[first_response, second_response]
        ),
        _stub_search(coach, passages),
    ):
        result = coach.ask_coach("Should I deload?")

    assert result["used_tools"] == ["search_coaching_docs"]
    assert result["citations"] == [
        {"document_id": 1, "document_title": "Deload Guidelines", "chunk_index": 2},
        {"document_id": 2, "document_title": "RPE and Autoregulation", "chunk_index": 0},
    ]


def test_ask_coach_deduplicates_repeated_passages_across_searches(coach: Coach) -> None:
    passage = {
        "document_id": 1,
        "document_title": "Deload Guidelines",
        "chunk_index": 2,
        "content": "Deload every four to six weeks.",
    }
    first_call = _tool_call("search_coaching_docs", '{"k": 5}', "call_1")
    second_call = _tool_call("search_coaching_docs", '{"k": 5}', "call_2")
    responses = [
        _response([first_call]),
        _response([second_call], response_id="resp_2"),
        _response([], "A deload is reasonable.", response_id="resp_3"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses),
        _stub_search(coach, {"status": "ok", "passages": [passage]}),
    ):
        result = coach.ask_coach("Should I deload?")

    assert result["citations"] == [
        {"document_id": 1, "document_title": "Deload Guidelines", "chunk_index": 2}
    ]


def test_ask_coach_reports_no_citations_when_nothing_matches(coach: Coach) -> None:
    tool_call = _tool_call("search_coaching_docs", '{"k": null}')
    responses = [
        _response([tool_call]),
        _response([], "I don't have material on marathon training.", response_id="resp_2"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses),
        _stub_search(coach, {"status": "no_match", "passages": []}),
    ):
        result = coach.ask_coach("How should I train for a marathon?")

    assert result["used_tools"] == ["search_coaching_docs"]
    assert result["citations"] == []


@pytest.mark.parametrize(
    ("tool_name", "arguments", "result"),
    [
        ("search_coaching_docs", '{"k": null}', {"status": "no_match", "passages": []}),
        ("search_coaching_docs", '{"k": null}', {"status": "empty_corpus", "passages": []}),
        (
            "query_workouts",
            '{"metric": "tonnage"}',
            {"result": "No matching workout data found."},
        ),
        ("query_exercises", "{}", []),
    ],
    ids=["retrieval-no-match", "empty-corpus", "no-workout-data", "empty-exercise-list"],
)
def test_ask_coach_normalizes_an_all_empty_outcome_to_nothing_found(
    coach: Coach,
    engine_logs: pytest.LogCaptureFixture,
    tool_name: str,
    arguments: str,
    result: Any,
) -> None:
    tool_call = _tool_call(tool_name, arguments)
    responses = [
        _response([tool_call]),
        _response([], "A paragraph reasoned over nothing.", response_id="resp_2"),
    ]
    question = "What did I lift last month?"

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        _stub_result(coach, tool_name, result),
    ):
        answer = coach.ask_coach(question)

    assert answer == {
        "answer": NOTHING_FOUND,
        "used_tools": [tool_name],
        "citations": [],
    }
    assert create.call_count == 2
    assert tool_name in engine_logs.text
    assert "nothing-found" in engine_logs.text
    assert question not in engine_logs.text


@pytest.mark.parametrize(
    ("tool_name", "arguments", "result", "expected_citations"),
    [
        (
            "query_workouts",
            '{"metric": "tonnage"}',
            {
                "metric": "tonnage",
                "group_by": "week",
                "result": [["Week of Jun 15, 2026", 10000.0]],
            },
            [],
        ),
        ("query_exercises", "{}", [[1, "Back Squat"]], []),
        (
            "search_coaching_docs",
            '{"k": null}',
            {"status": "ok", "passages": [PASSAGE]},
            [CITATION],
        ),
    ],
    ids=["data-rows", "exercise-list", "retrieved-passages"],
)
def test_ask_coach_ships_an_answer_backed_by_each_substantive_shape(
    coach: Coach,
    tool_name: str,
    arguments: str,
    result: Any,
    expected_citations: list[dict[str, Any]],
) -> None:
    tool_call = _tool_call(tool_name, arguments)
    responses = [
        _response([tool_call]),
        _response([], "Backed by a tool result.", response_id="resp_2"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses),
        _stub_result(coach, tool_name, result),
    ):
        answer = coach.ask_coach("What does my training show?")

    assert answer == {
        "answer": "Backed by a tool result.",
        "used_tools": [tool_name],
        "citations": expected_citations,
    }


def test_ask_coach_ships_a_mixed_answer_unchanged(coach: Coach) -> None:
    tool_calls = [
        _tool_call("search_coaching_docs", '{"k": null}', "call_search"),
        _tool_call("query_workouts", '{"metric": "tonnage"}', "call_workouts"),
    ]
    responses = [
        _response(tool_calls),
        _response(
            [],
            "Deload every four to six weeks; you have no squats logged.",
            response_id="resp_2",
        ),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        _stub_search(coach, {"status": "ok", "passages": [PASSAGE]}),
        _stub_tool(coach, "query_workouts", {"result": "No matching workout data found."}),
    ):
        answer = coach.ask_coach("Should I deload, and how much did I squat?")

    assert answer == {
        "answer": "Deload every four to six weeks; you have no squats logged.",
        "used_tools": ["search_coaching_docs", "query_workouts"],
        "citations": [CITATION],
    }
    assert create.call_count == 2


def test_ask_coach_drops_collected_citations_when_the_model_writes_no_text(
    coach: Coach,
) -> None:
    tool_call = _tool_call("search_coaching_docs", '{"k": null}')
    responses = [
        _response([tool_call]),
        _response([], "", response_id="resp_2"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses),
        _stub_search(coach, {"status": "ok", "passages": [PASSAGE]}),
    ):
        answer = coach.ask_coach("Should I deload?")

    assert answer == {
        "answer": COULD_NOT_COMPLETE,
        "used_tools": ["search_coaching_docs"],
        "citations": [],
    }


def test_ask_coach_collects_evidence_across_every_turn(coach: Coach) -> None:
    workout_call = _tool_call("query_workouts", '{"metric": "tonnage"}', "call_workouts")
    search_call = _tool_call("search_coaching_docs", '{"k": null}', "call_search")
    responses = [
        _response([workout_call]),
        _response([search_call], response_id="resp_2"),
        _response([], "You lifted 10,000 kg this week.", response_id="resp_3"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses),
        _stub_tool(
            coach,
            "query_workouts",
            {
                "metric": "tonnage",
                "group_by": "week",
                "result": [["Week of Jun 15, 2026", 10000.0]],
            },
        ),
        _stub_search(coach, {"status": "no_match", "passages": []}),
    ):
        answer = coach.ask_coach("How much did I squat, and should I deload?")

    assert answer["answer"] == "You lifted 10,000 kg this week."
    assert answer["used_tools"] == ["query_workouts", "search_coaching_docs"]


def test_ask_coach_searches_with_the_exact_question(coach: Coach) -> None:
    tool_call = _tool_call("search_coaching_docs", '{"k": null}')
    responses = [
        _response([tool_call]),
        _response([], "No match.", response_id="resp_2"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses),
        _stub_search(coach, {"status": "no_match", "passages": []}) as search,
    ):
        coach.ask_coach("Which lifting shoes should I buy?")

    search.assert_called_once_with("Which lifting shoes should I buy?", k=None)


def test_ask_coach_ignores_a_stray_query_argument(coach: Coach) -> None:
    tool_call = _tool_call("search_coaching_docs", '{"query": "deload", "k": 5}')
    responses = [
        _response([tool_call]),
        _response([], "No match.", response_id="resp_2"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses),
        _stub_search(coach, {"status": "no_match", "passages": []}) as search,
    ):
        coach.ask_coach("Should I deload?")

    search.assert_called_once_with("Should I deload?", k=5)


def test_ask_coach_re_sends_instructions_and_tools_on_every_turn(coach: Coach) -> None:
    tool_call = _tool_call("query_workouts", '{"metric": "tonnage"}')
    responses = [
        _response([tool_call]),
        _response([], "Done.", response_id="resp_2"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        _stub_tool(
            coach,
            "query_workouts",
            {
                "metric": "tonnage",
                "group_by": "week",
                "result": [["Week of Jun 15, 2026", 10000.0]],
            },
        ),
    ):
        coach.ask_coach("How much did I squat this week?")

    assert create.call_count == 2
    first_instructions = create.call_args_list[0].kwargs["instructions"]
    assert first_instructions
    assert create.call_args_list[1].kwargs["instructions"] == first_instructions
    assert create.call_args_list[1].kwargs["tools"] == coach.TOOLS


def test_ask_coach_answers_an_unknown_tool_with_an_error_result(
    coach: Coach, engine_logs: pytest.LogCaptureFixture
) -> None:
    unknown_call = _tool_call("query_nutrition", "{}", "call_unknown")
    responses = [
        _response([unknown_call], response_id="resp_1"),
        _response(
            [_tool_call("query_workouts", '{"metric": "tonnage"}', "call_workouts")],
            response_id="resp_2",
        ),
        _response([], "I can answer from your training data instead.", response_id="resp_3"),
    ]
    question = "How is my squat trending?"

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        _stub_tool(
            coach,
            "query_workouts",
            {
                "metric": "tonnage",
                "group_by": "week",
                "result": [["Week of Jun 15, 2026", 10000.0]],
            },
        ),
    ):
        result = coach.ask_coach(question)

    assert result == {
        "answer": "I can answer from your training data instead.",
        "used_tools": ["query_workouts"],
        "citations": [],
    }

    follow_up = create.call_args_list[1].kwargs["input"]
    assert len(follow_up) == 1
    assert follow_up[0]["type"] == "function_call_output"
    assert follow_up[0]["call_id"] == "call_unknown"
    error_result = json.loads(follow_up[0]["output"])
    assert error_result["tool"] == "query_nutrition"
    assert "Unknown tool" in error_result["error"]
    assert "query_nutrition" in error_result["error"]
    assert "query_nutrition" in engine_logs.text
    assert question not in engine_logs.text


@pytest.mark.parametrize(
    "arguments",
    [
        "not json",
        "[]",
        "null",
        '{"metric": "pace"}',
    ],
)
def test_ask_coach_answers_unreadable_arguments_with_an_error(coach: Coach, arguments: str) -> None:
    tool = MagicMock(return_value={"metric": "tonnage", "result": []})
    tool_call = _tool_call("query_workouts", arguments, "call_bad")
    responses = [
        _response([tool_call]),
        _response(
            [_tool_call("query_exercises", "{}", "call_exercises")],
            response_id="resp_2",
        ),
        _response([], "I can still answer.", response_id="resp_3"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        patch.dict(coach.TOOL_REGISTRY, {"query_workouts": tool}),
        _stub_tool(coach, "query_exercises", [[1, "Back Squat"]]),
    ):
        result = coach.ask_coach("How much did I squat this week?")

    assert result == {
        "answer": "I can still answer.",
        "used_tools": ["query_exercises"],
        "citations": [],
    }
    tool.assert_not_called()

    follow_up = create.call_args_list[1].kwargs["input"]
    assert len(follow_up) == 1
    assert follow_up[0]["call_id"] == "call_bad"
    error_result = json.loads(follow_up[0]["output"])
    assert error_result["tool"] == "query_workouts"
    assert "Could not read the arguments" in error_result["error"]
    assert "query_workouts" in error_result["error"]


def test_ask_coach_gives_every_tool_call_exactly_one_result(coach: Coach) -> None:
    tool_calls = [
        _tool_call("query_workouts", '{"metric": "tonnage"}', "call_ok"),
        _tool_call("query_nutrition", "{}", "call_unknown"),
        _tool_call("query_workouts", "not json", "call_broken"),
    ]
    responses = [
        _response(tool_calls),
        _response([], "Here is the answer.", response_id="resp_2"),
    ]

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        _stub_tool(
            coach,
            "query_workouts",
            {
                "metric": "tonnage",
                "group_by": "week",
                "result": [["Week of Jun 15, 2026", 10000.0]],
            },
        ),
    ):
        result = coach.ask_coach("How much did I squat this week?")

    assert result["answer"] == "Here is the answer."
    assert result["used_tools"] == ["query_workouts"]

    follow_up = create.call_args_list[1].kwargs["input"]
    assert [item["call_id"] for item in follow_up] == [
        "call_ok",
        "call_unknown",
        "call_broken",
    ]
    assert all(item["type"] == "function_call_output" for item in follow_up)
    assert len(follow_up) == len(tool_calls)


def test_ask_coach_returns_could_not_complete_when_iterations_run_out(
    coach: Coach, engine_logs: pytest.LogCaptureFixture
) -> None:
    search_call = _tool_call("search_coaching_docs", '{"k": null}', "call_search")
    workout_calls = [
        _tool_call("query_workouts", '{"metric": "tonnage"}', f"call_workouts_{index}")
        for index in range(4)
    ]
    never_run = _tool_call("query_exercises", "{}", "call_never")
    responses = [
        _response([search_call], response_id="resp_1"),
        *[
            _response([tool_call], response_id=f"resp_{index + 2}")
            for index, tool_call in enumerate(workout_calls)
        ],
        _response([never_run], response_id="resp_6"),
    ]
    passage = {
        "document_id": 1,
        "document_title": "Deload Guidelines",
        "chunk_index": 2,
        "content": "Deload every four to six weeks.",
    }
    question = "Should I deload after this block?"

    with (
        patch.object(coach.client.responses, "create", side_effect=responses) as create,
        _stub_search(coach, {"status": "ok", "passages": [passage]}),
        _stub_tool(coach, "query_workouts", {"metric": "tonnage", "result": []}),
    ):
        result = coach.ask_coach(question)

    assert create.call_count == 6
    assert result == {
        "answer": COULD_NOT_COMPLETE,
        "used_tools": ["search_coaching_docs", "query_workouts"],
        "citations": [],
    }
    assert "query_exercises" not in result["used_tools"]
    assert "search_coaching_docs" in engine_logs.text
    assert "query_workouts" in engine_logs.text
    assert question not in engine_logs.text
    assert "You are Spottr" not in engine_logs.text
