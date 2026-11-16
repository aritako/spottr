from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.api.repository.exercises import ExercisesRepository
from app.api.repository.workouts import WorkoutsRepository
from app.core.models import Exercise, Workout
from app.core.models import Set as SetModel
from app.shared.constants import NO_MATCHING_WORKOUT_DATA
from app.shared.enums.coach import Metric
from app.shared.enums.workouts import UnitEnum
from app.shared.errors.exercises import ExerciseNotFoundError
from app.shared.metrics import (
    DatedE1RM,
    DatedE1RMByExercise,
    DatedTonnage,
    DatedTonnageByExercise,
    GroupBy,
    e1rm_by_exercise,
    e1rm_over_time,
    estimated_one_rep_max,
    set_tonnage,
    tonnage_by_exercise,
    tonnage_over_time,
    workout_tonnage,
)
from app.shared.schemas.analytics import (
    AnalyticsBucket,
    ExerciseSeriesRead,
    ExerciseSessionRead,
    SessionSetRead,
    TopSetRead,
)

NO_DATA_RESULT: dict[str, str] = {"result": NO_MATCHING_WORKOUT_DATA}


class AnalyticsHandler:
    """Build analytics responses from workout data for the REST API and the coach tools."""

    def __init__(self, db: Session):
        self.workoutsRepository = WorkoutsRepository(db)
        self.exercisesRepository = ExercisesRepository(db)

    def read_series(
        self,
        exercise_id: int,
        metric: Metric = Metric.TONNAGE,
        start_date: date | None = None,
        end_date: date | None = None,
        group_by: GroupBy = "week",
    ) -> ExerciseSeriesRead:
        metric = Metric(metric)
        exercise = self._require_exercise(exercise_id)
        buckets = self._buckets_for_exercise_id(exercise.id, metric, start_date, end_date, group_by)
        return ExerciseSeriesRead(
            exercise_id=exercise.id,
            metric=metric,
            group_by=group_by,
            buckets=buckets,
        )

    def read_sessions(
        self,
        exercise_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 0,
        page_size: int = 10,
    ) -> list[ExerciseSessionRead]:
        exercise = self._require_exercise(exercise_id)
        workouts = self.workoutsRepository.list_workouts_for_exercise(
            exercise.id, start_date, end_date, page, page_size
        )
        if not workouts:
            return []

        sets_by_workout: dict[int, list[SetModel]] = defaultdict(list)
        for set_ in self.workoutsRepository.get_sets_for_workouts(
            [workout.id for workout in workouts], exercise.id
        ):
            sets_by_workout[set_.workout_id].append(set_)

        return [self._session_row(workout, sets_by_workout[workout.id]) for workout in workouts]

    def query_workouts(
        self,
        metric: Metric = Metric.TONNAGE,
        exercise: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        group_by: GroupBy = "week",
    ) -> dict[str, Any]:
        """Shape workout analytics for the coach's query_workouts tool."""
        metric = Metric(metric)
        if exercise is not None:
            resolved = self.exercisesRepository.get_by_name(exercise)
            if resolved is None:
                return dict(NO_DATA_RESULT)
            series = self.read_series(resolved.id, metric, start_date, end_date, group_by)
            if not series.buckets:
                return dict(NO_DATA_RESULT)
            return {
                "metric": metric.value,
                "group_by": group_by,
                "exercise": resolved.name,
                "buckets": [bucket.model_dump() for bucket in series.buckets],
            }

        sets = self.workoutsRepository.get_sets_for_all_exercises(start_date, end_date)
        if not sets:
            return dict(NO_DATA_RESULT)

        grouped = self._buckets_grouped_by_exercise(metric, sets, group_by)
        series = [
            {
                "exercise": name,
                "buckets": [bucket.model_dump() for bucket in buckets],
            }
            for name, buckets in sorted(grouped.items())
        ]
        if metric == Metric.TONNAGE:
            series.append(
                {
                    "exercise": "total",
                    "buckets": [
                        bucket.model_dump()
                        for bucket in self._buckets_for_sets(metric, sets, group_by)
                    ],
                }
            )
        return {"metric": metric.value, "group_by": group_by, "series": series}

    def _buckets_grouped_by_exercise(
        self, metric: Metric, sets: list[SetModel], group_by: GroupBy
    ) -> dict[str, list[AnalyticsBucket]]:
        if metric == Metric.TONNAGE:
            tonnage_entries = [
                DatedTonnageByExercise(
                    exercise=set_.exercise.name,
                    date=set_.workout.performed_at.date(),
                    tonnage=set_tonnage(float(set_.weight), set_.reps),
                )
                for set_ in sets
            ]
            grouped = tonnage_by_exercise(tonnage_entries, group_by)
        else:
            e1rm_entries = [
                DatedE1RMByExercise(
                    exercise=set_.exercise.name,
                    date=set_.workout.performed_at.date(),
                    e1rm=estimated_one_rep_max(float(set_.weight), set_.reps),
                )
                for set_ in sets
            ]
            grouped = e1rm_by_exercise(e1rm_entries, group_by)
        return {
            name: [AnalyticsBucket(label=label, value=value) for label, value in points]
            for name, points in grouped.items()
        }

    def _session_row(self, workout: Workout, sets: list[SetModel]) -> ExerciseSessionRead:
        ordered_sets = sorted(sets, key=lambda set_: (set_.set_index, set_.id))
        top_set = ordered_sets[0]
        top_e1rm = estimated_one_rep_max(float(top_set.weight), top_set.reps)
        for set_ in ordered_sets[1:]:
            e1rm = estimated_one_rep_max(float(set_.weight), set_.reps)
            if e1rm > top_e1rm:
                top_set = set_
                top_e1rm = e1rm

        return ExerciseSessionRead(
            workout_id=workout.id,
            performed_at=workout.performed_at,
            unit=UnitEnum(workout.unit),
            sets=[
                SessionSetRead(
                    weight=float(set_.weight),
                    reps=set_.reps,
                    rpe=set_.rpe,
                    set_index=set_.set_index,
                )
                for set_ in ordered_sets
            ],
            top_set=TopSetRead(weight=float(top_set.weight), reps=top_set.reps),
            e1rm=top_e1rm,
            tonnage=workout_tonnage(
                [{"weight": float(set_.weight), "reps": set_.reps} for set_ in ordered_sets]
            ),
        )

    def _require_exercise(self, exercise_id: int) -> Exercise:
        exercise = self.exercisesRepository.get(exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError()
        return exercise

    def _buckets_for_exercise_id(
        self,
        exercise_id: int,
        metric: Metric,
        start_date: date | None,
        end_date: date | None,
        group_by: GroupBy,
    ) -> list[AnalyticsBucket]:
        sets = self.workoutsRepository.get_sets_for_exercise(exercise_id, start_date, end_date)
        return self._buckets_for_sets(metric, sets, group_by)

    def _buckets_for_sets(
        self, metric: Metric, sets: list[SetModel], group_by: GroupBy
    ) -> list[AnalyticsBucket]:
        """The one aggregation pipeline shared by the REST series and the coach tool."""
        if metric == Metric.TONNAGE:
            entries = [
                DatedTonnage(
                    date=set_.workout.performed_at.date(),
                    tonnage=set_tonnage(float(set_.weight), set_.reps),
                )
                for set_ in sets
            ]
            points = tonnage_over_time(entries, group_by)
        else:
            entries = [
                DatedE1RM(
                    date=set_.workout.performed_at.date(),
                    e1rm=estimated_one_rep_max(float(set_.weight), set_.reps),
                )
                for set_ in sets
            ]
            points = e1rm_over_time(entries, group_by)
        return [AnalyticsBucket(label=label, value=value) for label, value in points]
