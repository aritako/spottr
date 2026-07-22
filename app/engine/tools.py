from datetime import date
from tokenize import group
from typing import Literal

from sqlalchemy.orm import Session

from app.api.handlers.exercises import ExercisesHandler
from app.api.handlers.workouts import WorkoutsHandler
from app.core.models import Set
from app.engine.helpers import (
    DatedE1RM,
    DatedTonnage,
    e1rm_over_time,
    estimated_one_rep_max,
    set_tonnage,
    tonnage_over_time,
)
from app.shared.enums.coach import Metric


class Tools:
    def __init__(self, db: Session):
        self.db = db
        self.exercisesHandler = ExercisesHandler(db)
        self.workoutsHandler = WorkoutsHandler(db)

    def query_exercises(self):
        exercises = self.exercisesHandler.read_exercise_list(page=0, page_size=100)
        return [(e.id, e.name) for e in exercises]

    def query_workouts(
        self,
        metric: Metric = Metric.TONNAGE,
        exercise: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        group_by: Literal["day", "week", "year", "month"] | None = None,
    ):
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        group_by = group_by or "week"
        sets: list[Set] = self.workoutsHandler.get_sets_for_metrics(exercise, start, end)

        if not sets:
            return {"result": "No matching workout data found."}
        match metric:
            case Metric.TONNAGE:
                entries = [
                    DatedTonnage(
                        date=s.workout.performed_at.date(),
                        tonnage=set_tonnage(float(s.weight), s.reps),
                    )
                    for s in sets
                ]
                result = tonnage_over_time(entries, group_by)
                return {"metric": "tonnage", "group_by": group_by, "result": result}
            case Metric.E1RM:
                entries = [
                    DatedE1RM(
                        date=s.workout.performed_at.date(),
                        e1rm=estimated_one_rep_max(float(s.weight), s.reps),
                    )
                    for s in sets
                ]
                result = e1rm_over_time(entries, group_by)
                return {"metric": "e1rm", "group_by": group_by, "result": result}
            case _:
                return {"result": "Metric not yet implemented."}
