from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.api.handlers.analytics import AnalyticsHandler
from app.api.handlers.docs import DocsHandler
from app.api.handlers.exercises import ExercisesHandler
from app.shared.enums.coach import Metric
from app.shared.metrics import GroupBy


class Tools:
    def __init__(self, db: Session):
        self.db = db
        self.docsHandler = DocsHandler(db)
        self.exercisesHandler = ExercisesHandler(db)
        self.analyticsHandler = AnalyticsHandler(db)

    def query_exercises(self):
        exercises = self.exercisesHandler.read_exercise_list(page=0, page_size=100)
        return [(e.id, e.name) for e in exercises]

    def query_workouts(
        self,
        metric: Metric = Metric.TONNAGE,
        exercise: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        group_by: GroupBy | None = None,
    ):
        return self.analyticsHandler.query_workouts(
            metric=Metric(metric),
            exercise=exercise,
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
            group_by=group_by or "week",
        )

    def search_coaching_docs(self, question: str, k: int | None = None) -> dict[str, Any]:
        return self.docsHandler.retrieve(question, k).model_dump(mode="json")
