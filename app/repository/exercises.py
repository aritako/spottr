from sqlalchemy import select
from sqlalchemy.orm.session import Session

from app.models import Exercise
from app.schemas.exercises import ExerciseCreate


class ExercisesRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Exercise | None:
        return self.db.get(Exercise, id)

    def list(self) -> list[Exercise]:
        return list(self.db.scalars(select(Exercise)))

    def create(self, exercise: ExerciseCreate) -> Exercise:
        new_exercise = Exercise(
            name=exercise.name,
            category=exercise.category,
            is_compound=exercise.is_compound,
        )
        self.db.add(new_exercise)
        self.db.commit()
        return new_exercise
