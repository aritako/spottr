from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.api.handlers.analytics import AnalyticsHandler
from app.core.models import Exercise, Workout
from app.core.models import Set as SetModel
from app.shared.enums.coach import Metric

NO_DATA = {"result": "No matching workout data found."}


def _handler() -> AnalyticsHandler:
    return AnalyticsHandler(MagicMock())


def _exercise(exercise_id: int, name: str) -> Exercise:
    return Exercise(id=exercise_id, name=name)


def _workout(workout_id: int, performed_at: datetime, unit: str = "kg") -> Workout:
    return Workout(id=workout_id, performed_at=performed_at, unit=unit)


def _set(
    exercise: Exercise,
    workout: Workout,
    weight: str,
    reps: int,
    set_index: int = 0,
    rpe: float | None = None,
) -> SetModel:
    return SetModel(
        exercise=exercise,
        workout=workout,
        exercise_id=exercise.id,
        workout_id=workout.id,
        weight=Decimal(weight),
        reps=reps,
        rpe=rpe,
        set_index=set_index,
    )


def test_metric_enum_only_contains_the_built_metrics() -> None:
    assert [metric.value for metric in Metric] == ["e1rm", "tonnage"]


def test_query_workouts_with_an_exercise_returns_one_series() -> None:
    handler = _handler()
    squat = _exercise(1, "Back Squat")
    first = _workout(10, datetime(2026, 6, 15, 12, tzinfo=UTC))
    second = _workout(11, datetime(2026, 6, 22, 12, tzinfo=UTC))
    sets = [_set(squat, first, "100.00", 5), _set(squat, second, "120.00", 5)]

    with (
        patch.object(handler.exercisesRepository, "get_by_name", return_value=squat),
        patch.object(handler.workoutsRepository, "get_sets_for_exercise", return_value=sets),
    ):
        result = handler.query_workouts(Metric.TONNAGE, "Back Squat", None, None, "week")

    assert result == {
        "metric": "tonnage",
        "group_by": "week",
        "exercise": "Back Squat",
        "buckets": [
            {"label": "Week of Jun 15, 2026", "value": 500.0},
            {"label": "Week of Jun 22, 2026", "value": 600.0},
        ],
    }


def test_query_workouts_echoes_the_applied_date_range() -> None:
    handler = _handler()
    squat = _exercise(1, "Back Squat")
    workout = _workout(10, datetime(2026, 6, 15, 12, tzinfo=UTC))
    sets = [_set(squat, workout, "100.00", 5)]

    with (
        patch.object(handler.exercisesRepository, "get_by_name", return_value=squat),
        patch.object(handler.workoutsRepository, "get_sets_for_exercise", return_value=sets),
    ):
        result = handler.query_workouts(
            Metric.TONNAGE, "Back Squat", date(2026, 6, 1), date(2026, 6, 30), "week"
        )

    assert result["start_date"] == "2026-06-01"
    assert result["end_date"] == "2026-06-30"


def test_query_workouts_echoes_the_date_range_when_nothing_matches() -> None:
    handler = _handler()

    with patch.object(handler.exercisesRepository, "get_by_name", return_value=None):
        result = handler.query_workouts(
            Metric.TONNAGE, "Bench Press", date(2026, 10, 20), date(2026, 11, 20), "week"
        )

    assert result == {
        "result": "No matching workout data found.",
        "start_date": "2026-10-20",
        "end_date": "2026-11-20",
    }


def test_read_series_coerces_a_raw_metric_string() -> None:
    handler = _handler()
    squat = _exercise(1, "Back Squat")
    workout = _workout(10, datetime(2026, 6, 15, 12, tzinfo=UTC))
    sets = [_set(squat, workout, "100.00", 5)]

    with (
        patch.object(handler.exercisesRepository, "get", return_value=squat),
        patch.object(handler.workoutsRepository, "get_sets_for_exercise", return_value=sets),
    ):
        result = handler.read_series(1, "tonnage")  # type: ignore[arg-type]

    assert result.model_dump(mode="json") == {
        "exercise_id": 1,
        "metric": "tonnage",
        "group_by": "week",
        "buckets": [{"label": "Week of Jun 15, 2026", "value": 500.0}],
    }


def test_query_workouts_coerces_a_raw_metric_string() -> None:
    handler = _handler()
    squat = _exercise(1, "Back Squat")
    workout = _workout(10, datetime(2026, 6, 15, 12, tzinfo=UTC))
    sets = [_set(squat, workout, "100.00", 5)]

    with (
        patch.object(handler.exercisesRepository, "get_by_name", return_value=squat),
        patch.object(handler.exercisesRepository, "get", return_value=squat),
        patch.object(handler.workoutsRepository, "get_sets_for_exercise", return_value=sets),
    ):
        result = handler.query_workouts("tonnage", "Back Squat")  # type: ignore[arg-type]

    assert result == {
        "metric": "tonnage",
        "group_by": "week",
        "exercise": "Back Squat",
        "buckets": [{"label": "Week of Jun 15, 2026", "value": 500.0}],
    }


def _per_exercise_sets() -> list[SetModel]:
    squat = _exercise(1, "Back Squat")
    bench = _exercise(2, "Bench Press")
    return [
        _set(squat, _workout(10, datetime(2026, 6, 15, 12, tzinfo=UTC)), "100.00", 5),
        _set(bench, _workout(11, datetime(2026, 6, 16, 12, tzinfo=UTC)), "80.00", 10),
        _set(squat, _workout(12, datetime(2026, 6, 22, 12, tzinfo=UTC)), "120.00", 5),
        _set(bench, _workout(13, datetime(2026, 6, 23, 12, tzinfo=UTC)), "90.00", 10),
    ]


def test_query_workouts_without_an_exercise_returns_per_exercise_series_and_tonnage_total() -> None:
    handler = _handler()

    with patch.object(
        handler.workoutsRepository, "get_sets_for_all_exercises", return_value=_per_exercise_sets()
    ):
        result = handler.query_workouts(Metric.TONNAGE, None, None, None, "week")

    assert result == {
        "metric": "tonnage",
        "group_by": "week",
        "series": [
            {
                "exercise": "Back Squat",
                "buckets": [
                    {"label": "Week of Jun 15, 2026", "value": 500.0},
                    {"label": "Week of Jun 22, 2026", "value": 600.0},
                ],
            },
            {
                "exercise": "Bench Press",
                "buckets": [
                    {"label": "Week of Jun 15, 2026", "value": 800.0},
                    {"label": "Week of Jun 22, 2026", "value": 900.0},
                ],
            },
            {
                "exercise": "total",
                "buckets": [
                    {"label": "Week of Jun 15, 2026", "value": 1300.0},
                    {"label": "Week of Jun 22, 2026", "value": 1500.0},
                ],
            },
        ],
    }


def test_query_workouts_without_an_exercise_never_totals_e1rm_across_exercises() -> None:
    handler = _handler()

    with patch.object(
        handler.workoutsRepository, "get_sets_for_all_exercises", return_value=_per_exercise_sets()
    ):
        result = handler.query_workouts(Metric.E1RM, None, None, None, "week")

    assert result == {
        "metric": "e1rm",
        "group_by": "week",
        "series": [
            {
                "exercise": "Back Squat",
                "buckets": [
                    {"label": "Week of Jun 15, 2026", "value": 116.67},
                    {"label": "Week of Jun 22, 2026", "value": 140.0},
                ],
            },
            {
                "exercise": "Bench Press",
                "buckets": [
                    {"label": "Week of Jun 15, 2026", "value": 106.67},
                    {"label": "Week of Jun 22, 2026", "value": 120.0},
                ],
            },
        ],
    }
    assert all(series["exercise"] != "total" for series in result["series"])


def test_query_workouts_returns_no_data_for_an_unknown_exercise_name() -> None:
    handler = _handler()

    with patch.object(handler.exercisesRepository, "get_by_name", return_value=None):
        result = handler.query_workouts(Metric.TONNAGE, "Not A Lift", None, None, "week")

    assert result == NO_DATA


def test_query_workouts_returns_no_data_when_the_exercise_has_no_sets() -> None:
    handler = _handler()
    squat = _exercise(1, "Back Squat")

    with (
        patch.object(handler.exercisesRepository, "get_by_name", return_value=squat),
        patch.object(handler.workoutsRepository, "get_sets_for_exercise", return_value=[]),
    ):
        result = handler.query_workouts(Metric.TONNAGE, "Back Squat", None, None, "week")

    assert result == NO_DATA


def test_query_workouts_returns_no_data_when_the_range_has_no_sets() -> None:
    handler = _handler()

    with patch.object(handler.workoutsRepository, "get_sets_for_all_exercises", return_value=[]):
        result = handler.query_workouts(Metric.TONNAGE, None, None, None, "week")

    assert result == NO_DATA
