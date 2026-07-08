from datetime import date

from sqlalchemy.orm import Session

from app.engine.helpers import (
    DatedE1RM,
    DatedTonnage,
    estimated_one_rep_max,
    set_tonnage,
    weekly_e1rm,
    weekly_tonnage,
)
from app.enums.coach import Metric
from app.handlers.workouts import WorkoutsHandler
from app.models import Set


class Tools:
    def __init__(self, db: Session):
        self.db = db
        self.workoutsHandler = WorkoutsHandler(db)

    def query_workouts(
        self,
        metric: Metric = Metric.TONNAGE,
        exercise: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        group_by: str | None = None,
    ):
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None

        sets: list[Set] = self.workoutsHandler.get_sets_for_metrics(exercise, start, end)

        if not sets:
            return {"result": "No matching workout data found."}
        match metric:
            case Metric.TONNAGE:
                entries = [
                    DatedTonnage(
                        date=s.workout.performed_at.date(),
                        tonnage=set_tonnage(s.weight, s.reps),
                    )
                    for s in sets
                ]
                result = weekly_tonnage(entries)
                return {"metric": metric.value, "weekly": result}
            case Metric.E1RM:
                entries = [
                    DatedE1RM(
                        date=s.workout.performed_at.date(),
                        e1rm=estimated_one_rep_max(float(s.weight), s.reps),
                    )
                    for s in sets
                ]
                result = weekly_e1rm(entries)
                return {"metric": metric.value, "weekly": result}
            case _:
                return {"result": "Metric not yet implemented."}
