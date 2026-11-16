from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.handlers.analytics import AnalyticsHandler
from app.core.db import get_db
from app.shared.enums.coach import Metric
from app.shared.errors.exercises import ExerciseNotFoundError
from app.shared.metrics import GroupBy
from app.shared.schemas.analytics import ExerciseSeriesRead, ExerciseSessionRead

router = APIRouter()


@router.get("/exercises/{exercise_id}/series", response_model=ExerciseSeriesRead)
def get_exercise_series(
    db: Annotated[Session, Depends(get_db)],
    exercise_id: int,
    metric: Annotated[Metric, Query()] = Metric.TONNAGE,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    group_by: Annotated[GroupBy, Query()] = "week",
) -> ExerciseSeriesRead:
    handler = AnalyticsHandler(db)
    try:
        return handler.read_series(exercise_id, metric, start_date, end_date, group_by)
    except ExerciseNotFoundError as e:
        raise HTTPException(status_code=404, detail="Exercise not found.") from e


@router.get("/exercises/{exercise_id}/sessions", response_model=list[ExerciseSessionRead])
def get_exercise_sessions(
    db: Annotated[Session, Depends(get_db)],
    exercise_id: int,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=0)] = 0,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[ExerciseSessionRead]:
    handler = AnalyticsHandler(db)
    try:
        return handler.read_sessions(exercise_id, start_date, end_date, page, page_size)
    except ExerciseNotFoundError as e:
        raise HTTPException(status_code=404, detail="Exercise not found.") from e
