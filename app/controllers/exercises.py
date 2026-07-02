from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm.session import Session

from app.db import get_db
from app.handlers.exercises import ExercisesHandler
from app.schemas.exercises import ExerciseCreate, ExerciseRead, ExerciseReadResponse

router = APIRouter()


@router.get("/{id}", response_model=ExerciseRead | None)
def get_exercise(
    db: Annotated[Session, Depends(get_db)],
    id: int,
):
    handler = ExercisesHandler(db)
    return handler.read_exercise(id)


@router.get("", response_model=list[ExerciseRead])
def get_exercises(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(0, ge=0),
    page_size: int = Query(10, ge=1, le=100),
):
    handler = ExercisesHandler(db)
    return handler.read_exercise_list(page, page_size)


@router.post("", status_code=201, response_model=ExerciseReadResponse)
def create_exercise(
    db: Annotated[Session, Depends(get_db)],
    exercise: ExerciseCreate,
):
    handler = ExercisesHandler(db)
    new_exercise = handler.create_exercise(exercise)
    return ExerciseReadResponse(id=new_exercise.id)
