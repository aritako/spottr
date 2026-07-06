from sqlalchemy.orm import Session

from app.enums.coach import Metric
from app.handlers.workouts import WorkoutsHandler


class Tools:
    def __init__(self, db: Session):
        self.db = db
        self.workoutsHandler = WorkoutsHandler(db)

    def query_workouts(
        self,
        exercise: str,
        metric: Metric,
        start_date: str | None = None,
        end_date: str | None = None,
        group_by: str | None = None,
    ):
        pass
