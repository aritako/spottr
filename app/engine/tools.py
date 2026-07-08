from datetime import date

from sqlalchemy.orm import Session

from app.enums.coach import Metric
from app.handlers.workouts import WorkoutsHandler
from app.schemas.workouts import SetRead


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

        pass
