from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm.session import Session

from app.api.handlers.workouts import WorkoutsHandler
from app.core.db import get_db
from app.shared.errors.exercises import ExerciseNotFoundError
from app.shared.schemas.workouts import WorkoutCreate, WorkoutRead, WorkoutReadResponse

router = APIRouter()


@router.get("/{id}", response_model=WorkoutRead | None)
def get_workout(db: Annotated[Session, Depends(get_db)], id: int) -> WorkoutRead | None:
    handler = WorkoutsHandler(db)
    return handler.read_workout(id)


@router.get("", response_model=list[WorkoutRead])
def get_workouts(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(0, ge=0),
    page_size: int = Query(10, ge=1, le=100),
) -> list[WorkoutRead]:
    handler = WorkoutsHandler(db)
    return handler.read_workout_list(page, page_size)


@router.post("", status_code=201, response_model=WorkoutReadResponse)
def create_workout(
    db: Annotated[Session, Depends(get_db)],
    workout: WorkoutCreate,
):
    handler = WorkoutsHandler(db)
    try:
        new_workout = handler.create_workout(workout)
    except ExerciseNotFoundError as e:
        raise HTTPException(status_code=404, detail="Invalid exercise id.") from e
    return WorkoutReadResponse(id=new_workout.id)
