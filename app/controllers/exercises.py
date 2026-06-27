from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm.session import Session

from app.db import get_db
from app.handlers.exercises import ExercisesHandler
from app.schemas.exercises import ExerciseCreate, ExerciseRead

router = APIRouter()


@router.get("", response_model=list[ExerciseRead] | ExerciseRead | None)
def get_exercises(
    db: Annotated[Session, Depends(get_db)],
    id: int | None = None,
):
    handler = ExercisesHandler(db)
    if id:
        return handler.read_exercise(id)
    else:
        return handler.read_exercise_list()


@router.post("", status_code=201, response_model=ExerciseRead)
def create_exercise(
    db: Annotated[Session, Depends(get_db)],
    exercise: ExerciseCreate,
):
    handler = ExercisesHandler(db)
    return handler.create_exercise(exercise)
