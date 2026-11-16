from datetime import date

import pytest

from app.shared.metrics import (
    DatedE1RM,
    DatedE1RMByExercise,
    DatedTonnage,
    DatedTonnageByExercise,
    e1rm_by_exercise,
    e1rm_over_time,
    estimated_one_rep_max,
    set_tonnage,
    tonnage_by_exercise,
    tonnage_over_time,
    workout_tonnage,
)


def test_estimated_one_rep_max_uses_the_epley_estimate() -> None:
    assert estimated_one_rep_max(100.0, 5) == 116.67
    assert estimated_one_rep_max(100.0, 1) == 100.0
    assert estimated_one_rep_max(100.0, 0) == 0.0


def test_set_tonnage_multiplies_weight_by_reps() -> None:
    assert set_tonnage(102.5, 3) == 307.5


def test_workout_tonnage_sums_the_sets() -> None:
    assert workout_tonnage([{"weight": 100.0, "reps": 5}, {"weight": 102.5, "reps": 3}]) == 807.5
    assert workout_tonnage([]) == 0.0


@pytest.mark.parametrize(
    ("group_by", "expected"),
    [
        (
            "day",
            [
                ("Dec 29, 2025", 100.0),
                ("Jan 01, 2026", 200.0),
                ("Jan 08, 2026", 120.0),
                ("Feb 03, 2026", 50.0),
            ],
        ),
        (
            "week",
            [
                ("Week of Dec 29, 2025", 300.0),
                ("Week of Jan 05, 2026", 120.0),
                ("Week of Feb 02, 2026", 50.0),
            ],
        ),
        (
            "month",
            [("Dec 2025", 100.0), ("Jan 2026", 320.0), ("Feb 2026", 50.0)],
        ),
        ("year", [("2025", 100.0), ("2026", 370.0)]),
    ],
)
def test_tonnage_by_exercise_uses_the_requested_grain(
    group_by: str, expected: list[tuple[str, float]]
) -> None:
    entries = [
        DatedTonnageByExercise(exercise="bench", date=date(2025, 12, 29), tonnage=100.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 1), tonnage=200.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 8), tonnage=120.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 2, 3), tonnage=50.0),
    ]

    assert tonnage_by_exercise(entries, group_by) == {"bench": expected}  # type: ignore[arg-type]


def test_tonnage_by_exercise_separates_exercises_and_sorts_each_chronologically() -> None:
    entries = [
        DatedTonnageByExercise(exercise="squat", date=date(2026, 1, 8), tonnage=90.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 8), tonnage=120.0),
        DatedTonnageByExercise(exercise="squat", date=date(2026, 1, 1), tonnage=80.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 1), tonnage=100.0),
        DatedTonnageByExercise(exercise="squat", date=date(2025, 12, 30), tonnage=70.0),
        DatedTonnageByExercise(exercise="bench", date=date(2025, 12, 30), tonnage=90.0),
    ]

    assert tonnage_by_exercise(entries, "week") == {
        "bench": [
            ("Week of Dec 29, 2025", 190.0),
            ("Week of Jan 05, 2026", 120.0),
        ],
        "squat": [
            ("Week of Dec 29, 2025", 150.0),
            ("Week of Jan 05, 2026", 90.0),
        ],
    }


def test_tonnage_by_exercise_defaults_to_weekly_buckets() -> None:
    entries = [DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 1), tonnage=100.0)]

    assert tonnage_by_exercise(entries) == {"bench": [("Week of Dec 29, 2025", 100.0)]}


@pytest.mark.parametrize(
    ("group_by", "expected"),
    [
        (
            "day",
            [
                ("Dec 29, 2025", 90.0),
                ("Jan 01, 2026", 110.0),
                ("Jan 08, 2026", 105.0),
                ("Feb 03, 2026", 95.0),
            ],
        ),
        (
            "week",
            [
                ("Week of Dec 29, 2025", 110.0),
                ("Week of Jan 05, 2026", 105.0),
                ("Week of Feb 02, 2026", 95.0),
            ],
        ),
        (
            "month",
            [("Dec 2025", 90.0), ("Jan 2026", 110.0), ("Feb 2026", 95.0)],
        ),
        ("year", [("2025", 90.0), ("2026", 110.0)]),
    ],
)
def test_e1rm_by_exercise_keeps_the_maximum_per_bucket(
    group_by: str, expected: list[tuple[str, float]]
) -> None:
    entries = [
        DatedE1RMByExercise(exercise="bench", date=date(2025, 12, 29), e1rm=90.0),
        DatedE1RMByExercise(exercise="bench", date=date(2026, 1, 1), e1rm=100.0),
        DatedE1RMByExercise(exercise="bench", date=date(2026, 1, 1), e1rm=110.0),
        DatedE1RMByExercise(exercise="bench", date=date(2026, 1, 8), e1rm=105.0),
        DatedE1RMByExercise(exercise="bench", date=date(2026, 2, 3), e1rm=95.0),
    ]

    assert e1rm_by_exercise(entries, group_by) == {"bench": expected}  # type: ignore[arg-type]


def test_e1rm_by_exercise_separates_exercises_and_keeps_each_maximum() -> None:
    entries = [
        DatedE1RMByExercise(exercise="squat", date=date(2026, 1, 1), e1rm=140.0),
        DatedE1RMByExercise(exercise="bench", date=date(2026, 1, 1), e1rm=100.0),
        DatedE1RMByExercise(exercise="squat", date=date(2026, 1, 8), e1rm=145.0),
        DatedE1RMByExercise(exercise="bench", date=date(2026, 1, 8), e1rm=105.0),
        DatedE1RMByExercise(exercise="squat", date=date(2026, 1, 1), e1rm=142.0),
    ]

    assert e1rm_by_exercise(entries, "week") == {
        "squat": [("Week of Dec 29, 2025", 142.0), ("Week of Jan 05, 2026", 145.0)],
        "bench": [("Week of Dec 29, 2025", 100.0), ("Week of Jan 05, 2026", 105.0)],
    }


def test_tonnage_over_time_sums_each_bucket() -> None:
    entries = [
        DatedTonnage(date=date(2026, 1, 1), tonnage=100.0),
        DatedTonnage(date=date(2026, 1, 2), tonnage=50.0),
        DatedTonnage(date=date(2026, 1, 8), tonnage=75.0),
    ]

    assert tonnage_over_time(entries) == [
        ("Week of Dec 29, 2025", 150.0),
        ("Week of Jan 05, 2026", 75.0),
    ]


def test_e1rm_over_time_keeps_each_bucket_maximum() -> None:
    entries = [
        DatedE1RM(date=date(2026, 1, 1), e1rm=100.0),
        DatedE1RM(date=date(2026, 1, 2), e1rm=120.0),
        DatedE1RM(date=date(2026, 1, 8), e1rm=110.0),
    ]

    assert e1rm_over_time(entries) == [
        ("Week of Dec 29, 2025", 120.0),
        ("Week of Jan 05, 2026", 110.0),
    ]
