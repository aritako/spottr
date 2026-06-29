from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.session import Session

from app.models import Workout
from app.schemas.workouts import WorkoutCreate


class WorkoutsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Workout | None:
        return self.db.get(Workout, id)

    def list(self, page: int, page_size: int = 10) -> list[Workout]:
        query = (
            select(Workout)
            .options(selectinload(Workout.sets))
            .offset(page * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(query))

    def create(self, workout: Workout) -> Workout:
        try:
            self.db.add(workout)
            self.db.commit()
            self.db.refresh(workout)
            return workout
        except Exception as e:
            self.db.rollback()
            raise e
