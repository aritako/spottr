import pytest

from app.engine.guardrails import (
    ScopeVerdict,
    ToolEvidence,
    ToolOutcome,
    error_evidence,
    scope_verdict,
    tool_evidence,
)

PASSAGE = {
    "document_id": 1,
    "document_title": "Deload Guidelines",
    "chunk_index": 2,
    "content": "Deload every four to six weeks.",
}


@pytest.mark.parametrize(
    ("tool", "result", "expected"),
    [
        # Retrieval reports emptiness in its status; Passages are the evidence.
        ("search_coaching_docs", {"status": "no_match", "passages": []}, ToolOutcome.EMPTY),
        ("search_coaching_docs", {"status": "empty_corpus", "passages": []}, ToolOutcome.EMPTY),
        (
            "search_coaching_docs",
            {"status": "ok", "passages": [PASSAGE]},
            ToolOutcome.SUBSTANTIVE,
        ),
        # Workout data arrives as rows; the no-matching-data result is a status string.
        (
            "query_workouts",
            {"metric": "tonnage", "group_by": "week", "result": [["2026-W01", 1000.0]]},
            ToolOutcome.SUBSTANTIVE,
        ),
        (
            "query_workouts",
            {"result": "No matching workout data found."},
            ToolOutcome.EMPTY,
        ),
        # Exercise data is a list of (id, name) pairs.
        ("query_exercises", [[1, "Back Squat"]], ToolOutcome.SUBSTANTIVE),
        ("query_exercises", [], ToolOutcome.EMPTY),
        # A result the rule cannot read is no evidence, never a false positive.
        ("query_nutrition", {"calories": 2500}, ToolOutcome.ERROR),
        ("search_coaching_docs", "unexpected", ToolOutcome.ERROR),
    ],
    ids=[
        "retrieval-no-match",
        "retrieval-empty-corpus",
        "retrieval-passages",
        "workout-rows",
        "workout-no-data",
        "exercise-list",
        "exercise-empty-list",
        "unknown-tool",
        "unreadable-shape",
    ],
)
def test_tool_evidence_uses_each_tools_real_result_shape(
    tool: str, result: object, expected: ToolOutcome
) -> None:
    assert tool_evidence(tool, result) == ToolEvidence(tool=tool, outcome=expected)


def _evidence(*outcomes: ToolOutcome) -> list[ToolEvidence]:
    return [
        ToolEvidence(tool=f"tool_{index}", outcome=outcome)
        for index, outcome in enumerate(outcomes)
    ]


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        ([], ScopeVerdict.NO_SUBSTANTIVE_CALL),
        (_evidence(ToolOutcome.ERROR), ScopeVerdict.NO_SUBSTANTIVE_CALL),
        (_evidence(ToolOutcome.ERROR, ToolOutcome.ERROR), ScopeVerdict.NO_SUBSTANTIVE_CALL),
        (_evidence(ToolOutcome.EMPTY), ScopeVerdict.ALL_EMPTY),
        (_evidence(ToolOutcome.EMPTY, ToolOutcome.EMPTY), ScopeVerdict.ALL_EMPTY),
        (_evidence(ToolOutcome.ERROR, ToolOutcome.EMPTY), ScopeVerdict.ALL_EMPTY),
        (_evidence(ToolOutcome.SUBSTANTIVE), ScopeVerdict.SUPPORTED),
        (_evidence(ToolOutcome.EMPTY, ToolOutcome.SUBSTANTIVE), ScopeVerdict.SUPPORTED),
        (
            _evidence(ToolOutcome.SUBSTANTIVE, ToolOutcome.EMPTY, ToolOutcome.ERROR),
            ScopeVerdict.SUPPORTED,
        ),
    ],
    ids=[
        "no-calls",
        "one-error",
        "only-errors",
        "one-empty",
        "every-result-empty",
        "error-with-empty",
        "one-substantive",
        "empty-then-substantive",
        "mixed",
    ],
)
def test_scope_verdict_judges_the_whole_loop(
    evidence: list[ToolEvidence], expected: ScopeVerdict
) -> None:
    assert scope_verdict(evidence) is expected


def test_error_evidence_is_never_an_empty_result() -> None:
    evidence = [error_evidence("query_nutrition")]

    assert evidence == [ToolEvidence(tool="query_nutrition", outcome=ToolOutcome.ERROR)]
    assert scope_verdict(evidence) is ScopeVerdict.NO_SUBSTANTIVE_CALL
