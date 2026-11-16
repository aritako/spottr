from decimal import Decimal

import pytest

from app.engine.guardrails import (
    SCRAPED_TOOLS,
    Receipts,
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
        # Any other status string is a capability outcome the model can fix, not emptiness.
        (
            "query_workouts",
            {"result": "Metric not yet implemented."},
            ToolOutcome.ERROR,
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
        "workout-unimplemented-metric",
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
        # An error outranks emptiness: a failed call is fixable, so it earns the retry.
        (_evidence(ToolOutcome.ERROR, ToolOutcome.EMPTY), ScopeVerdict.NO_SUBSTANTIVE_CALL),
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


def _group(*literal: str, series: tuple[str, ...] = ()) -> Receipts:
    return Receipts(
        literal=frozenset(Decimal(value) for value in literal),
        series=tuple(Decimal(value) for value in series),
    )


def _receipts(*values: str) -> list[Receipts]:
    """One tool result whose measurements are also literal Receipts."""
    return [_group(*values, series=values)]


def _numerals(*pairs: tuple[str, str]) -> list[tuple[str, Decimal]]:
    return [(text, Decimal(value)) for text, value in pairs]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Accepted numeral forms: each one is its own row.
        ("3 sets", _numerals(("3", "3"))),
        ("12,400 kg", _numerals(("12,400", "12400"))),
        ("12,400.50 kg", _numerals(("12,400.50", "12400.5"))),
        # A malformed grouping is not a thousands separator: each run of digits is its own
        # numeral and is checked independently.
        ("1,24,00 kg", _numerals(("1", "1"), ("24", "24"), ("00", "0"))),
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
        # A sign detached by a space is not part of the value; only orthographically attached
        # signs count, so "4 - 6" stays a range.
        ("- 5 kg", _numerals(("5", "5"))),
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
        "malformed-grouping-is-not-a-separator",
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
        "detached-sign-is-not-part-of-value",
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
    answer: str, receipts: list[Receipts], expected: str | None
) -> None:
    violation = grounding_violation(answer, receipts)

    if expected is None:
        assert violation is None
    else:
        assert violation is not None
        assert violation.numeral == expected


@pytest.mark.parametrize(
    ("tool", "result", "expected"),
    [
        (
            "query_workouts",
            {
                "metric": "tonnage",
                "group_by": "week",
                "result": [["Week of Jun 15, 2026", 12400.0]],
            },
            _group("15", "2026", "12400", series=("12400",)),
        ),
        # Exercise ids are identifiers, not measurements; their names carry no numerals here.
        ("query_exercises", [[1, "Back Squat"], [2, "Bench Press"]], _group()),
        (
            "search_coaching_docs",
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
            _group("4", "6", "20"),
        ),
        (
            "query_workouts",
            {"metric": "e1rm", "result": [["Week of Jun 15, 2026", 125.0]]},
            _group("15", "2026", "125", series=("125",)),
        ),
        ("query_workouts", {"result": "No matching workout data found."}, _group()),
        ("search_coaching_docs", {"status": "no_match", "passages": []}, _group()),
        ("query_exercises", [], _group()),
        ("query_workouts", "No matching workout data found.", _group()),
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
    tool: str, result: object, expected: Receipts
) -> None:
    assert scrape_receipts(tool, result) == expected


def test_every_scraped_tool_has_a_real_scraper() -> None:
    samples = {
        "search_coaching_docs": (
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
            ToolOutcome.SUBSTANTIVE,
            _group("4", "6", "20"),
        ),
        "query_workouts": (
            {"metric": "tonnage", "result": [["2026-W01", 1000.0]]},
            ToolOutcome.SUBSTANTIVE,
            _group("1", "2026", "1000", series=("1000",)),
        ),
        "query_exercises": (
            [[1, "2-Board Press"]],
            ToolOutcome.SUBSTANTIVE,
            _group("2"),
        ),
    }

    assert set(samples) == SCRAPED_TOOLS
    for tool, (sample, outcome, receipts) in samples.items():
        assert tool_evidence(tool, sample).outcome is outcome
        assert scrape_receipts(tool, sample) == receipts


def test_an_unarmed_tool_backs_nothing() -> None:
    assert scrape_receipts("query_nutrition", {"document_id": 15, "calories": 2500}) == _group()
    assert tool_evidence("query_nutrition", {"calories": 2500}).outcome is ToolOutcome.ERROR


def test_derivations_use_only_one_results_measurements() -> None:
    results = [_group("100", series=("100",)), _group("200", series=("200",))]

    assert grounding_violation("Total 300 kg.", results) is not None


def test_labels_are_literal_receipts_but_never_derivation_sources() -> None:
    workout = _group("15", "2026", "12400", "13400", series=("12400", "13400"))

    assert grounding_violation("You lifted 15,000 kg.", [workout]) is not None
    assert grounding_violation("You lifted 12,400 kg.", [workout]) is None


def test_repeated_measurements_sum_correctly() -> None:
    workout = _group(series=("10000", "20000", "20000"))

    assert grounding_violation("Total 50,000 kg.", [workout]) is None
    assert grounding_violation("Total 30,000 kg.", [workout]) is not None


def test_a_sum_uses_every_measurement_not_any_subset() -> None:
    workout = _group(series=("10000", "20000", "30000"))

    assert grounding_violation("Total 60,000 kg.", [workout]) is None
    assert grounding_violation("Total 30,000 kg.", [workout]) is not None


def test_identifiers_are_not_receipts() -> None:
    exercises = scrape_receipts("query_exercises", [[12, "Back Squat"]])
    passage = scrape_receipts(
        "search_coaching_docs",
        {
            "status": "ok",
            "passages": [
                {
                    "document_id": 15,
                    "document_title": "Deload Guidelines",
                    "chunk_index": 1,
                    "content": "2026 deload schedule.",
                }
            ],
        },
    )

    assert grounding_violation("You logged 12 exercises.", [exercises]) is not None
    assert grounding_violation("That is from 2,041.", [passage]) is not None
    assert grounding_violation("That is from 2026.", [passage]) is None


def test_equal_measurements_derive_a_zero_difference() -> None:
    workout = _group(series=("10000", "10000"))

    assert grounding_violation("No change: 0 kg.", [workout]) is None


@pytest.mark.parametrize(
    ("answer", "receipts", "expected"),
    [
        # Difference, both directions, and an exact decimal value.
        ("Up 2,000 kg.", _receipts("10000", "12000"), None),
        ("The change was -2,000 kg.", _receipts("10000", "12000"), None),
        ("Up 2,001 kg.", _receipts("10000", "12000"), "2,001"),
        ("The change was 0.2 kg.", _receipts("0.1", "0.3"), None),
        (
            "The change was 0.20000000000000004 kg.",
            _receipts("0.1", "0.3"),
            "0.20000000000000004",
        ),
        # Percentage change, both directions; a decrease is signed.
        ("Tonnage rose 20%.", _receipts("10000", "12000"), None),
        ("Tonnage fell -17%.", _receipts("10000", "12000"), None),
        ("Tonnage rose 25%.", _receipts("10000", "12500"), None),
        ("Tonnage fell -20%.", _receipts("10000", "12500"), None),
        ("Tonnage fell 17%.", _receipts("10000", "12000"), "17"),
        # The same pair does not license the wrong direction's figure.
        ("Tonnage rose 20%.", _receipts("10000", "12500"), "20"),
        # Whole-percent rounding is the only relaxation.
        ("Tonnage rose 33%.", _receipts("3000", "4000"), None),
        ("Tonnage rose 33.3%.", _receipts("3000", "4000"), "33.3"),
        # A written fractional statement is not "stated as a whole percent" even when its value
        # is integral: tenths precision supports 33.3, not 33.0.
        ("Tonnage rose 33.0%.", _receipts("3000", "4000"), "33.0"),
        ("Tonnage rose 33.00%.", _receipts("3000", "4000"), "33.00"),
        ("Tonnage rose 34%.", _receipts("3000", "4000"), "34"),
        ("Tonnage fell 16.7%.", _receipts("10000", "12000"), "16.7"),
        ("Tonnage rose 16%.", _receipts("10000", "12000"), "16"),
        ("Tonnage rose 12.5%.", _receipts("10000", "11250"), None),
        ("Tonnage rose 18%.", _receipts("1.1", "1.3"), None),
        ("Tonnage rose 18.2%.", _receipts("1.1", "1.3"), "18.2"),
        # Sum over a pair, a larger set, and exact decimals.
        ("Total 22,000 kg.", _receipts("10000", "12000"), None),
        ("Total 6,000 kg.", _receipts("1000", "2000", "3000"), None),
        ("Total 0.3 kg.", _receipts("0.1", "0.2"), None),
        ("Total 22,001 kg.", _receipts("10000", "12000"), "22,001"),
        (
            "Total 0.30000000000000004 kg.",
            _receipts("0.1", "0.2"),
            "0.30000000000000004",
        ),
        # Average over a pair, a larger set, and exact decimals.
        ("Average 11,000 kg.", _receipts("10000", "12000"), None),
        ("Average 11,000 kg.", _receipts("10000", "11000", "12000"), None),
        ("Average 0.15 kg.", _receipts("0.1", "0.2"), None),
        ("Average 11,001 kg.", _receipts("10000", "12000"), "11,001"),
        (
            "Average 0.15000000000000002 kg.",
            _receipts("0.1", "0.2"),
            "0.15000000000000002",
        ),
        # A recipe with no source pair or set produces nothing.
        ("Up 2,000 kg.", _receipts(), "2,000"),
        ("Up 2,000 kg.", _receipts("10000"), "2,000"),
        ("Total 20,000 kg.", _receipts("10000"), "20,000"),
        ("Average 15,000 kg.", _receipts("10000"), "15,000"),
        ("Up 20%.", _receipts(), "20"),
        ("Up 20%.", _receipts("10000"), "20"),
        # Neither literal nor derivable is still the unchanged Violation.
        ("You lifted 5,000 kg.", _receipts("10000", "12000"), "5,000"),
        ("You lifted 10,000 kg.", _receipts("10000"), None),
    ],
    ids=[
        "difference-increase",
        "difference-decrease-with-sign",
        "difference-near-miss",
        "difference-exact-decimal",
        "difference-representation-noise-is-not-a-receipt",
        "percentage-increase",
        "percentage-decrease-whole-rounded",
        "percentage-exact-increase",
        "percentage-exact-decrease",
        "percentage-decrease-without-sign",
        "percentage-wrong-direction",
        "percentage-whole-rounded",
        "percentage-fraction-not-supported",
        "percentage-written-tenths-is-not-whole",
        "percentage-written-hundredths-is-not-whole",
        "percentage-near-miss-whole",
        "percentage-decrease-fraction-not-supported",
        "percentage-wrong-whole-rounding",
        "percentage-exact-fraction",
        "percentage-whole-rounded-decimal-source",
        "percentage-representation-noise-not-supported",
        "sum-pair",
        "sum-three",
        "sum-exact-decimal",
        "sum-near-miss",
        "sum-representation-noise-is-not-a-receipt",
        "average-pair",
        "average-three",
        "average-exact-decimal",
        "average-near-miss",
        "average-representation-noise-is-not-a-receipt",
        "difference-no-receipts",
        "difference-single-receipt",
        "sum-single-receipt",
        "average-single-receipt",
        "percentage-no-receipts",
        "percentage-single-receipt",
        "unrelated-numeral-still-unbacked",
        "literal-still-backed",
    ],
)
def test_grounding_derivation_recipes(
    answer: str, receipts: list[Receipts], expected: str | None
) -> None:
    violation = grounding_violation(answer, receipts)

    if expected is None:
        assert violation is None
    else:
        assert violation is not None
        assert violation.numeral == expected
