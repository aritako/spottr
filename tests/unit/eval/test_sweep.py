import pytest

from app.eval.sweep import lock_cutoff, lock_top_k, sweep_cutoffs
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

    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(0.5)
    assert lock.margin == pytest.approx(0.6)
    assert lock.reason is None
    assert lock.report is not None
    assert lock.report.k == 5
    assert lock.report.recall == 1.0
    assert lock.report.no_match_rate == 1.0


def test_lock_cutoff_picks_the_widest_margin_that_still_meets_the_recall_bar() -> None:
    results = [
        *[
            _positive(f"near {index}", f"near-{index}.md", (f"near-{index}.md", 0.1))
            for index in range(19)
        ],
        _positive("far positive", "far.md", ("far.md", 0.6)),
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.9)) for index in range(10)],
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(0.5)
    assert lock.margin == pytest.approx(0.8)
    assert lock.report is not None
    assert lock.report.recall == pytest.approx(0.95)
    assert lock.report.no_match_rate == 1.0


def test_lock_cutoff_reports_the_margin_at_the_returned_cutoff() -> None:
    results = [
        *[
            _positive(f"near {index}", f"near-{index}.md", (f"near-{index}.md", 0.1))
            for index in range(19)
        ],
        _positive("late", "late.md", ("late.md", 0.2), ("late.md", 0.45)),
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.9)) for index in range(10)],
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(0.5)
    assert lock.margin == pytest.approx(0.45)
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


def test_lock_cutoff_refuses_to_lock_without_a_negative_passage() -> None:
    results = [
        _positive("positive", "doc.md", ("doc.md", 0.1)),
        _negative("negative"),
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is False
    assert lock.reason is not None
    assert "no Negative question returned a Passage" in lock.reason


def test_lock_cutoff_falls_back_when_the_centred_value_loses_recall() -> None:
    results = [
        *[
            _positive(f"positive {index}", f"doc-{index}.md", (f"doc-{index}.md", 0.5))
            for index in range(20)
        ],
        _negative("close negative", ("close.md", 0.4)),
        *[_negative(f"negative {index}", (f"other-{index}.md", 0.9)) for index in range(9)],
    ]

    lock = lock_cutoff(results)

    assert lock.qualifies is True
    assert lock.cutoff == pytest.approx(0.7)
    assert lock.margin == pytest.approx(-0.1)
    assert lock.report is not None
    assert lock.report.recall == 1.0
    assert lock.report.no_match_rate == pytest.approx(0.9)


def test_sweep_cutoffs_covers_each_retrieval_outcome() -> None:
    results = [
        _positive("positive", "doc.md", ("doc.md", 0.2)),
        _negative("negative", ("other.md", 0.8)),
    ]

    reports = sweep_cutoffs(results, k=5)

    assert [report.cutoff for report in reports] == pytest.approx([0.1, 0.5, 1.4])
    assert [report.recall for report in reports] == [0.0, 1.0, 1.0]
    assert [report.no_match_rate for report in reports] == [1.0, 1.0, 0.0]
