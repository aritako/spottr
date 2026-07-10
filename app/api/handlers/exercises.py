from fastapi import HTTPException
from sqlalchemy.orm.session import Session

from app.api.repository.exercises import ExercisesRepository
from app.core.models import Exercise
from app.shared.schemas.exercises import ExerciseCreate, ExerciseRead


class ExercisesHandler:
    def __init__(self, db: Session):
        self.repository = ExercisesRepository(db)

    def create_exercise(self, exercise: ExerciseCreate) -> ExerciseRead:
        exercise_model = Exercise(
            name=exercise.name,
            category=exercise.category,
            is_compound=exercise.is_compound,
        )
        new_exercise = self.repository.create(exercise_model)
        return ExerciseRead.model_validate(new_exercise)

    def read_exercise(self, id: int) -> ExerciseRead | None:
        exercise = self.repository.get(id)
        if exercise:
            return ExerciseRead.model_validate(exercise)
        raise HTTPException(status_code=404, detail="Exercise not found")

    def read_exercise_list(self, page: int, page_size: int) -> list[ExerciseRead]:
        exercises = self.repository.list_(page, page_size)
        return [ExerciseRead.model_validate(exercise) for exercise in exercises]
