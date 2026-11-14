import math
import random

import pytest

from app.eval.metrics import QuestionResult
from app.eval.sweep import (
    _meets_bars,
    lock_cutoff,
    lock_top_k,
    margin_bounds,
    negative_distance,
    positive_distance,
    required_count,
    sweep_cutoffs,
)
from tests.unit.eval.helpers import negative as _negative
from tests.unit.eval.helpers import positive as _positive


def test_lock_cutoff_centers_a_clean_gap_between_positives_and_negatives() -> None:
    results = [
        *[
            _positive(f"positive {index}", f"doc-{index}.md", (f"doc-{index}.md", 0.2))
            for index in range(20)
        ],
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.8)) for index in range(10)],
    ]

    # P: required_count(0.95, 20) = 19, so P is the 19th of 20 sorted positive distances = 0.2.
    # D: required_count(0.90, 10) = 9, so one leak is allowed and D is the 2nd of 10 = 0.8.
    # mid = (0.2 + 0.8) / 2 = 0.5; margin = D - P = 0.6.
    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(0.5)
    assert lock.margin == pytest.approx(0.6)
    assert lock.reason is None
    assert lock.report is not None
    assert lock.report.k == 5
    assert lock.report.recall == 1.0
    assert lock.report.no_match_rate == 1.0


def test_lock_cutoff_places_the_cutoff_at_the_midpoint_of_the_bounds() -> None:
    results = [
        *[
            _positive(f"near {index}", f"near-{index}.md", (f"near-{index}.md", 0.1))
            for index in range(19)
        ],
        _positive("far positive", "far.md", ("far.md", 0.6)),
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.9)) for index in range(10)],
    ]

    # P: required_count(0.95, 20) = 19, so P is the 19th of 20 sorted distances = 0.1.
    # D: required_count(0.90, 10) = 9, so D is the 2nd of 10 negatives = 0.9.
    # mid = (0.1 + 0.9) / 2 = 0.5; margin = D - P = 0.8.
    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(0.5)
    assert lock.margin == pytest.approx(0.8)
    assert lock.report is not None
    assert lock.report.recall == pytest.approx(0.95)
    assert lock.report.no_match_rate == 1.0


def test_lock_cutoff_reports_the_margin_as_the_distance_between_the_bounds() -> None:
    results = [
        *[
            _positive(f"near {index}", f"near-{index}.md", (f"near-{index}.md", 0.1))
            for index in range(19)
        ],
        _positive("late", "late.md", ("late.md", 0.2), ("late.md", 0.45)),
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.9)) for index in range(10)],
    ]

    # Positive distances: 19 at 0.1 and one at 0.2 (the nearest of the late pair).
    # P: required_count(0.95, 20) = 19 -> P = 0.1.
    # D: required_count(0.90, 10) = 9 -> D = 0.9.
    # mid = 0.5; margin = D - P = 0.8.
    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(0.5)
    assert lock.margin == pytest.approx(0.8)
    assert lock.report is not None
    assert lock.report.recall == 1.0
    assert lock.report.no_match_rate == 1.0


def test_lock_cutoff_reports_a_pure_recall_failure() -> None:
    results = [
        _positive("positive", "doc.md", ("doc.md", 2.0)),
        _negative("negative", ("other.md", 0.5)),
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "No cutoff reaches recall@5" in lock.reason


def test_lock_cutoff_reports_a_pure_no_match_failure() -> None:
    results = [
        _positive("positive", "doc.md", ("doc.md", 0.1)),
        _negative("negative", ("other.md", 0.0)),
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "No cutoff keeps Negative no_match >= 90%" in lock.reason


def test_lock_cutoff_failure_names_the_swept_k() -> None:
    results = [
        *[
            _positive(f"positive {index}", f"doc-{index}.md", (f"doc-{index}.md", 0.7))
            for index in range(20)
        ],
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.6)) for index in range(10)],
    ]

    lock = lock_cutoff(results, k=3)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "recall@3" in lock.reason


def test_lock_cutoff_reports_when_the_two_bars_conflict() -> None:
    results = [
        *[
            _positive(f"positive {index}", f"doc-{index}.md", (f"doc-{index}.md", 0.7))
            for index in range(20)
        ],
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.6)) for index in range(10)],
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is False
    assert lock.cutoff is None
    assert lock.report is None
    assert lock.margin is None
    assert lock.reason is not None
    assert "recall@5" in lock.reason
    assert "no_match" in lock.reason


def test_lock_cutoff_refuses_to_lock_without_negative_questions() -> None:
    results = [
        _positive("positive", "doc.md", ("doc.md", 0.1)),
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is False
    assert "Negative" in lock.reason


def test_lock_cutoff_refuses_to_lock_without_positive_questions() -> None:
    results = [_negative("negative", ("other.md", 0.9))]

    lock = lock_cutoff(results)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "no positive questions" in lock.reason


def test_lock_top_k_picks_the_smallest_k_that_reaches_the_recall_bar() -> None:
    results = [
        *[
            _positive(f"positive {index}", f"doc-{index}.md", (f"doc-{index}.md", 0.05))
            for index in range(9)
        ],
        _positive(
            "late positive",
            "late.md",
            ("wrong-1.md", 0.1),
            ("wrong-2.md", 0.2),
            ("wrong-3.md", 0.3),
            ("late.md", 0.4),
        ),
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.9)) for index in range(2)],
    ]

    lock = lock_top_k(results, cutoff=0.5)

    assert lock.qualifies is True
    assert lock.k == 4
    assert lock.cutoff == 0.5
    assert lock.reason is None
    assert lock.report is not None
    assert lock.report.recall == 1.0
    assert lock.report.no_match_rate == 1.0


def test_lock_top_k_reports_when_no_k_reaches_the_recall_bar() -> None:
    results = [
        _positive("positive", "doc.md", ("doc.md", 1.5)),
        _negative("negative", ("other.md", 0.9)),
    ]

    lock = lock_top_k(results, cutoff=0.5)

    assert lock.qualifies is False
    assert lock.k is None
    assert lock.report is None
    assert lock.reason is not None
    assert "recall" in lock.reason


def test_lock_top_k_reports_when_the_final_pair_fails_the_no_match_bar() -> None:
    results = [
        _positive("positive", "doc.md", ("doc.md", 0.1)),
        _negative("negative", ("other.md", 0.2)),
    ]

    lock = lock_top_k(results, cutoff=1.0)

    assert lock.qualifies is False
    assert lock.k is None
    assert lock.report is not None
    assert lock.report.recall == 1.0
    assert lock.report.no_match_rate == 0.0
    assert lock.reason is not None
    assert "bars conflict" in lock.reason


def test_lock_top_k_refuses_to_lock_without_positive_questions() -> None:
    results = [_negative("negative", ("other.md", 0.9))]

    lock = lock_top_k(results, cutoff=0.5)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "no positive questions" in lock.reason


def test_lock_top_k_refuses_to_lock_without_negative_questions() -> None:
    results = [_positive("positive", "doc.md", ("doc.md", 0.1))]

    lock = lock_top_k(results, cutoff=0.5)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "no Negative questions" in lock.reason


def test_lock_cutoff_treats_a_negative_without_passages_as_an_infinite_bound() -> None:
    results = [
        _positive("positive", "doc.md", ("doc.md", 0.1)),
        _negative("negative"),
    ]

    # P = 0.1 and D = inf. mid = (0.1 + min(inf, 2.0)) / 2 = 1.05.
    # margin = D - P = inf; the lock succeeds because P is finite.
    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(1.05)
    assert lock.margin == math.inf
    assert lock.report is not None
    assert lock.report.recall == 1.0
    assert lock.report.no_match_rate == 1.0


def test_lock_cutoff_places_the_cutoff_between_a_leaking_negative_and_the_positives() -> None:
    results = [
        *[
            _positive(f"positive {index}", f"doc-{index}.md", (f"doc-{index}.md", 0.5))
            for index in range(20)
        ],
        _negative("close negative", ("close.md", 0.4)),
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.9)) for index in range(9)],
    ]

    # P = 0.5 (all positives). D: required_count(0.90, 10) = 9, so one leak is allowed;
    # the negatives sorted are [0.4, 0.9 x 9], so D = 0.9. mid = 0.7; margin = 0.4.
    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(0.7)
    assert lock.margin == pytest.approx(0.4)
    assert lock.report is not None
    assert lock.report.recall == 1.0
    assert lock.report.no_match_rate == pytest.approx(0.9)


def test_positive_distance_uses_the_nearest_expected_document_passage() -> None:
    result = _positive("positive", "a.md", ("a.md", 0.6), ("a.md", 0.3))

    assert positive_distance(result, 5) == pytest.approx(0.3)


def test_positive_distance_is_infinite_outside_the_top_k() -> None:
    result = _positive(
        "positive",
        "a.md",
        ("b.md", 0.1),
        ("c.md", 0.2),
        ("d.md", 0.3),
        ("e.md", 0.4),
        ("f.md", 0.5),
        ("a.md", 0.6),
    )

    assert math.isinf(positive_distance(result, 5))
    assert positive_distance(result, 6) == pytest.approx(0.6)


def test_negative_distance_is_infinite_without_passages() -> None:
    assert math.isinf(negative_distance(_negative("negative")))


def test_margin_bounds_allows_one_leak_in_ten_negatives() -> None:
    results = [
        _positive("positive", "a.md", ("a.md", 0.1)),
        *[_negative(f"negative {index}", ("b.md", 0.4 + index / 10)) for index in range(10)],
    ]

    p_bound, d_bound = margin_bounds(results, k=5)

    assert p_bound == pytest.approx(0.1)
    assert d_bound == pytest.approx(0.5)  # the second-smallest negative distance


def test_a_positive_at_the_distance_ceiling_is_not_ranked() -> None:
    result = _positive("positive", "a.md", ("a.md", 2.0))

    assert math.isinf(positive_distance(result, 5))


def test_lock_cutoff_reports_a_ranking_failure_without_an_assertion_error() -> None:
    results = [
        _positive("positive one", "a.md", ("a.md", 2.0)),
        _positive("positive two", "a.md", ("a.md", 2.0)),
        _negative("negative", ("b.md", 0.5)),
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "ranking failure" in lock.reason


def test_lock_cutoff_reason_names_both_bounds_when_they_overlap() -> None:
    results = [
        _positive("positive", "a.md", ("a.md", 0.7)),
        _negative("negative", ("b.md", 0.6)),
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "P=0.7000" in lock.reason
    assert "D=0.6000" in lock.reason


def test_required_count_matches_the_scorers_rate_comparison() -> None:
    assert required_count(0.95, 70) == 67
    assert required_count(0.90, 12) == 11
    assert required_count(0.90, 22) == 20


def test_lock_cutoff_uses_four_decimals_when_three_fall_outside_the_interval() -> None:
    results = [
        _positive("positive", "a.md", ("a.md", 0.5)),
        _negative("negative", ("b.md", 0.5009)),
    ]

    # P = 0.5, D = 0.5009, mid = 0.50045. round(mid, 3) = 0.5, which is not > P;
    # round(mid, 4) = 0.5005, which is inside (P, D].
    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(0.5005)


def test_lock_cutoff_refuses_an_interval_too_narrow_for_four_decimals() -> None:
    results = [
        _positive("positive", "a.md", ("a.md", 0.50001)),
        _negative("negative", ("b.md", 0.50002)),
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "4-decimal precision" in lock.reason


def test_lock_cutoff_agrees_with_the_sweep_on_randomized_cases() -> None:
    rng = random.Random(0)
    sources = ["a.md", "b.md", "c.md"]
    qualified = 0
    unqualified = 0

    for _ in range(200):
        results: list[QuestionResult] = []
        for index in range(rng.randint(5, 25)):
            passages = [("a.md", round(rng.uniform(0.2, 0.6), 2))]
            for _ in range(rng.randint(0, 5)):
                passages.append((rng.choice(sources), round(rng.uniform(0.2, 0.9), 2)))
            results.append(_positive(f"positive {index}", "a.md", *passages))

        for index in range(rng.randint(3, 12)):
            passages = [
                (rng.choice(sources), round(rng.uniform(0.5, 0.9), 2))
                for _ in range(rng.randint(0, 6))
            ]
            results.append(_negative(f"negative {index}", *passages))

        lock = lock_cutoff(results)
        sweep_qualifies = any(_meets_bars(report) for report in sweep_cutoffs(results))
        assert lock.qualifies == sweep_qualifies

        if lock.qualifies:
            qualified += 1
        else:
            unqualified += 1

    assert qualified >= 20
    assert unqualified >= 20


def test_sweep_cutoffs_covers_each_retrieval_outcome() -> None:
    results = [
        _positive("positive", "doc.md", ("doc.md", 0.2)),
        _negative("negative", ("other.md", 0.8)),
    ]

    reports = sweep_cutoffs(results, k=5)

    assert [report.cutoff for report in reports] == pytest.approx([0.1, 0.5, 1.4])
    assert [report.recall for report in reports] == [0.0, 1.0, 1.0]
    assert [report.no_match_rate for report in reports] == [1.0, 1.0, 0.0]
