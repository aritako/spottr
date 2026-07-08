from sqlalchemy import select
from sqlalchemy.orm.session import Session

from app.models import Exercise
from app.schemas.exercises import ExerciseCreate


class ExercisesRepository:
    def __init__(self, db: Session):
        self.db = db

    def check(self, ids: set[int]) -> set[int]:
        query = select(Exercise.id).where(Exercise.id.in_(ids))
        return set(self.db.scalars(query))

    def get(self, id: int) -> Exercise | None:
        return self.db.get(Exercise, id)

    def list_(self, page: int, page_size: int) -> list[Exercise]:
        query = select(Exercise).offset(page * page_size).limit(page_size)
        return list(self.db.scalars(query))

    def create(self, exercise: Exercise) -> Exercise:
        try:
            self.db.add(exercise)
            self.db.commit()
            self.db.refresh(exercise)
            return exercise
        except Exception as e:
            self.db.rollback()
            raise e
