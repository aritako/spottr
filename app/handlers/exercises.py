from sqlalchemy.orm.session import Session

from app.repository.exercises import ExercisesRepository
from app.schemas.exercises import ExerciseCreate


class ExercisesHandler:
    def __init__(self, db: Session):
        self.repository = ExercisesRepository(db)

    def create_exercise(self, exercise: ExerciseCreate):
        new_exercise = self.repository.create(exercise)
        return new_exercise

    def read_exercise(self, id: int):
        return self.repository.get(id)

    def read_exercise_list(self):
        return self.repository.list()
