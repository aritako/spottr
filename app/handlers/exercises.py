from sqlalchemy.orm.session import Session

from app.repository.exercises import ExercisesRepository
from app.schemas.exercises import ExerciseCreate, ExerciseRead


class ExercisesHandler:
    def __init__(self, db: Session):
        self.repository = ExercisesRepository(db)

    def create_exercise(self, exercise: ExerciseCreate) -> ExerciseRead:
        new_exercise = self.repository.create(exercise)
        return ExerciseRead.model_validate(new_exercise)

    def read_exercise(self, id: int) -> ExerciseRead | None:
        exercise = self.repository.get(id)
        if exercise is None:
            return None
        return ExerciseRead.model_validate(exercise)

    def read_exercise_list(self) -> list[ExerciseRead]:
        exercises = self.repository.list()
        return [ExerciseRead.model_validate(exercise) for exercise in exercises]
