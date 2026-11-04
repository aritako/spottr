import pytest

from app.eval.metrics import score
from tests.unit.eval.helpers import negative as _negative
from tests.unit.eval.helpers import positive as _positive


def test_recall_at_k_counts_the_expected_document_in_the_top_k() -> None:
    result = _positive(
        "When should I deload?",
        "deloads.md",
        ("other.md", 0.1),
        ("deloads.md", 0.2),
        ("deloads.md", 0.3),
    )

    at_one = score([result], k=1, cutoff=1.0)
    at_two = score([result], k=2, cutoff=1.0)
    at_three = score([result], k=3, cutoff=1.0)

    assert at_one.recall == 0.0
    assert at_one.precision == 0.0
    assert at_one.retrieved == 1
    assert at_two.recall == 1.0
    assert at_two.precision == 0.5
    assert at_two.retrieved == 2
    assert at_three.recall == 1.0
    assert at_three.precision == pytest.approx(2 / 3)


def test_cutoff_excludes_passages_at_or_beyond_the_threshold() -> None:
    result = _positive("When should I deload?", "deloads.md", ("deloads.md", 0.5))

    excluded = score([result], k=5, cutoff=0.5)
    included = score([result], k=5, cutoff=0.5001)

    assert excluded.recall == 0.0
    assert excluded.retrieved == 0
    assert included.recall == 1.0
    assert included.retrieved == 1


def test_no_match_rate_counts_negative_questions_without_passages() -> None:
    results = [
        _positive("When should I deload?", "deloads.md", ("deloads.md", 0.1)),
        _negative("What was my squat e1RM?", ("workouts.md", 0.4)),
        _negative("How do I bake sourdough?", ("bread.md", 0.9)),
    ]

    at_point_five = score(results, k=5, cutoff=0.5)
    at_point_three = score(results, k=5, cutoff=0.3)

    assert at_point_five.no_match_rate == 0.5
    assert at_point_three.no_match_rate == 1.0


def test_margins_compare_the_worst_positive_hit_with_the_best_negative_passage() -> None:
    results = [
        _positive(
            "When should I deload?",
            "deloads.md",
            ("deloads.md", 0.2),
            ("deloads.md", 0.3),
            ("other.md", 0.7),
            ("other.md", 0.8),
        ),
        _positive("How much volume?", "volume.md", ("volume.md", 0.2)),
        _negative("What was my squat e1RM?", ("workouts.md", 0.4)),
    ]

    report = score(results, k=4, cutoff=1.0)

    first, second, third = report.margins
    assert first.worst_positive_distance == 0.3
    assert first.best_negative_distance == 0.7
    assert first.margin == pytest.approx(0.4)
    assert second.worst_positive_distance == 0.2
    assert second.best_negative_distance is None
    assert second.margin is None
    assert third.worst_positive_distance is None
    assert third.best_negative_distance == 0.4
    assert third.margin is None


def test_precision_is_measured_across_every_retrieved_passage() -> None:
    results = [
        _positive(
            "When should I deload?",
            "deloads.md",
            ("deloads.md", 0.1),
            ("other.md", 0.2),
        ),
        _negative("What was my squat e1RM?", ("workouts.md", 0.3)),
    ]

    report = score(results, k=5, cutoff=1.0)

    assert report.recall == 1.0
    assert report.no_match_rate == 0.0
    assert report.retrieved == 3
    assert report.precision == pytest.approx(1 / 3)


def test_scoring_sorts_passages_by_distance_before_applying_k() -> None:
    result = _positive(
        "When should I deload?",
        "deloads.md",
        ("deloads.md", 0.5),
        ("other.md", 0.1),
        ("deloads.md", 0.2),
    )

    assert score([result], k=1, cutoff=1.0).recall == 0.0
    assert score([result], k=2, cutoff=1.0).recall == 1.0


def test_margin_is_undefined_when_no_negative_passage_is_retrieved() -> None:
    result = _positive(
        "When should I deload?",
        "deloads.md",
        ("deloads.md", 0.2),
        ("other.md", 0.8),
    )

    entry_margin = score([result], k=1, cutoff=1.0).margins[0]

    assert entry_margin.worst_positive_distance == 0.2
    assert entry_margin.best_negative_distance is None
    assert entry_margin.margin is None


def test_margin_reflects_the_selected_top_k() -> None:
    result = _positive(
        "When should I deload?",
        "deloads.md",
        ("deloads.md", 0.2),
        ("other.md", 0.8),
    )

    at_one = score([result], k=1, cutoff=1.0).margins[0]
    at_two = score([result], k=2, cutoff=1.0).margins[0]

    assert at_one.margin is None
    assert at_two.best_negative_distance == 0.8
    assert at_two.margin == pytest.approx(0.6)


def test_scoring_without_entries_reports_zeroed_rates() -> None:
    report = score([], k=5, cutoff=0.5)

    assert report.recall == 0.0
    assert report.no_match_rate == 0.0
    assert report.precision == 0.0
    assert report.retrieved == 0
    assert report.margins == ()


def test_scoring_rejects_a_non_positive_k() -> None:
    with pytest.raises(ValueError):
        score([], k=0, cutoff=0.5)
