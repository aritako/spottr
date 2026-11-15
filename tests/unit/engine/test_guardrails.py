from decimal import Decimal

import pytest

from app.engine.guardrails import (
    ScopeVerdict,
    ToolEvidence,
    ToolOutcome,
    error_evidence,
    extract_numerals,
    grounding_violation,
    scope_verdict,
    scrape_receipts,
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


def _receipts(*values: str) -> frozenset[Decimal]:
    return frozenset(Decimal(value) for value in values)


def _numerals(*pairs: tuple[str, str]) -> list[tuple[str, Decimal]]:
    return [(text, Decimal(value)) for text, value in pairs]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Accepted numeral forms: each one is its own row.
        ("3 sets", _numerals(("3", "3"))),
        ("12,400 kg", _numerals(("12,400", "12400"))),
        ("12,400.50 kg", _numerals(("12,400.50", "12400.5"))),
        ("12400.0", _numerals(("12400.0", "12400"))),
        ("12400.00", _numerals(("12400.00", "12400"))),
        ("72.5 kg", _numerals(("72.5", "72.5"))),
        (".5 kg", _numerals((".5", "0.5"))),
        ("12400kg", _numerals(("12400", "12400"))),
        ("20%", _numerals(("20", "20"))),
        ("1st place", _numerals(("1", "1"))),
        ("10k", _numerals(("10", "10"))),
        ("e1RM", _numerals(("1", "1"))),
        ("5x5", _numerals(("5", "5"), ("5", "5"))),
        ("-5 kg", _numerals(("-5", "-5"))),
        ("\u22125 kg", _numerals(("\u22125", "-5"))),
        ("+5 kg", _numerals(("+5", "5"))),
        # Ranges, fractions, and dates are checked one numeral at a time.
        ("4-6 weeks", _numerals(("4", "4"), ("6", "6"))),
        ("4\u20136 weeks", _numerals(("4", "4"), ("6", "6"))),
        ("4 to 6 weeks", _numerals(("4", "4"), ("6", "6"))),
        ("12,400-13,000", _numerals(("12,400", "12400"), ("13,000", "13000"))),
        ("1/2 inch", _numerals(("1", "1"), ("2", "2"))),
        ("2026-06-15", _numerals(("2026", "2026"), ("06", "6"), ("15", "15"))),
        ("Week of Jun 15, 2026", _numerals(("15", "15"), ("2026", "2026"))),
        ("12,400.", _numerals(("12,400", "12400"))),
        ("1e5", _numerals(("1e5", "100000"))),
        ("1.5e3", _numerals(("1.5e3", "1500"))),
        # Not numerals at all.
        ("four to six weeks", []),
        ("twenty percent", []),
        ("Block IV", []),
        ("no digits here at all", []),
    ],
    ids=[
        "plain-integer",
        "thousands-separator",
        "thousands-and-fraction",
        "trailing-decimal",
        "trailing-zeros",
        "decimal",
        "leading-dot",
        "attached-unit",
        "percent-sign",
        "ordinal-suffix",
        "k-suffix-is-not-a-multiplier",
        "digit-inside-a-word",
        "sets-by-reps",
        "leading-minus-sign",
        "unicode-minus-sign",
        "explicit-plus-sign",
        "hyphenated-range",
        "en-dash-range",
        "worded-range",
        "range-with-thousands",
        "fraction-endpoints",
        "iso-date",
        "bucket-label",
        "sentence-period",
        "scientific-notation",
        "scientific-notation-with-fraction",
        "spelled-out",
        "spelled-out-percent",
        "roman-numeral",
        "no-numerals",
    ],
)
def test_extract_numerals_checks_every_form_independently(
    text: str, expected: list[tuple[str, Decimal]]
) -> None:
    assert [(numeral.text, numeral.value) for numeral in extract_numerals(text)] == expected


@pytest.mark.parametrize(
    ("answer", "receipts", "expected"),
    [
        # A numeral equal after format normalization is backed.
        ("You lifted 12,400 kg.", _receipts("12400.0"), None),
        ("You lifted 12,400 kg.", _receipts("12400"), None),
        ("You lifted 12400.0 kg.", _receipts("12400"), None),
        ("You lifted 12,400 kg.", _receipts("12400.00"), None),
        ("You lifted 72.5 kg.", _receipts("72.50"), None),
        ("You lifted 8,675.5 kg.", _receipts("8675.50"), None),
        # Close is not equal: there is no tolerance band.
        ("You lifted 12,401 kg.", _receipts("12400"), "12,401"),
        ("You lifted 12,399 kg.", _receipts("12400"), "12,399"),
        ("You lifted 12,400.01 kg.", _receipts("12400"), "12,400.01"),
        # Every numeral is checked on its own.
        ("You lifted 12,400 kg over 5 weeks.", _receipts("12400"), "5"),
        ("You lifted 12,400 kg over 5 weeks.", _receipts("12400", "5"), None),
        ("Deload every 4-6 weeks.", _receipts("4"), "6"),
        ("Deload every 4-6 weeks.", _receipts("6"), "4"),
        ("Deload every 4-6 weeks.", _receipts("4", "6"), None),
        ("Use a 1/2 inch lift.", _receipts("1"), "2"),
        ("Use a 1/2 inch lift.", _receipts("1", "2"), None),
        ("The block starts Jun 15, 2026.", _receipts("15", "2026"), None),
        ("The block starts Jun 15, 2026.", _receipts("2026"), "15"),
        # Signs, percent signs, unit suffixes, and identifiers each follow their decision.
        ("The change was -5 kg.", _receipts("-5"), None),
        ("The change was -5 kg.", _receipts("5"), "-5"),
        ("An RPE of 20% is high.", _receipts("20"), None),
        ("An RPE of 20% is high.", _receipts("0.2"), "20"),
        ("Add 10k of volume.", _receipts("10"), None),
        ("Add 10k of volume.", _receipts("10000"), "10"),
        ("Your e1RM is 12,400.", _receipts("1", "12400"), None),
        ("Your e1RM is 12,400.", _receipts("12400"), "1"),
        # Spelled-out numerals never violate, with or without receipts.
        ("Deload every four to six weeks.", _receipts(), None),
        ("Deload every four to six weeks.", _receipts("4", "6"), None),
        ("No numerals here.", _receipts(), None),
        ("", _receipts(), None),
    ],
    ids=[
        "thousands-against-trailing-decimal",
        "thousands-against-integer",
        "trailing-decimal-in-answer",
        "trailing-zeros-in-receipt",
        "decimal-receipt",
        "thousands-and-decimal-receipt",
        "near-miss-above",
        "near-miss-below",
        "near-miss-fraction",
        "one-unbacked-among-supported",
        "several-numerals-all-backed",
        "range-missing-upper-end",
        "range-missing-lower-end",
        "range-both-ends-backed",
        "fraction-missing-second-endpoint",
        "fraction-both-endpoints-backed",
        "date-components-backed",
        "date-missing-day",
        "negative-backed",
        "negative-sign-is-part-of-value",
        "percent-against-number",
        "percent-is-not-a-fraction",
        "unit-suffix-ignored",
        "k-suffix-is-not-a-multiplier",
        "identifier-digit-backed",
        "identifier-digit-needs-its-own-receipt",
        "spelled-out",
        "spelled-out-with-unused-receipts",
        "no-numerals",
        "empty-answer",
    ],
)
def test_grounding_violation_requires_an_exact_receipt(
    answer: str, receipts: frozenset[Decimal], expected: str | None
) -> None:
    violation = grounding_violation(answer, receipts)

    if expected is None:
        assert violation is None
    else:
        assert violation is not None
        assert violation.numeral == expected


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (
            {
                "metric": "tonnage",
                "group_by": "week",
                "result": [["Week of Jun 15, 2026", 12400.0]],
            },
            _receipts("15", "2026", "12400"),
        ),
        ([[1, "Back Squat"], [2, "Bench Press"]], _receipts("1", "2")),
        (
            {
                "status": "ok",
                "passages": [
                    {
                        "document_id": 1,
                        "document_title": "Deload Guidelines",
                        "chunk_index": 2,
                        "content": "Deload every 4 to 6 weeks for 20% less volume.",
                    }
                ],
            },
            _receipts("1", "2", "4", "6", "20"),
        ),
        (
            {"metric": "e1rm", "result": [["Week of Jun 15, 2026", 125.0]]},
            _receipts("1", "15", "2026", "125"),
        ),
        ({"result": "No matching workout data found."}, frozenset()),
        ({"status": "no_match", "passages": []}, frozenset()),
        ([], frozenset()),
        ("No matching workout data found.", frozenset()),
    ],
    ids=[
        "workout-rows-and-bucket-label",
        "exercise-list",
        "retrieved-passage-text-and-metadata",
        "e1rm-rows",
        "no-workout-data",
        "retrieval-no-match",
        "empty-exercise-list",
        "string-result",
    ],
)
def test_scrape_receipts_reads_every_tool_output_shape(
    result: object, expected: frozenset[Decimal]
) -> None:
    assert scrape_receipts(result) == expected
