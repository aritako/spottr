from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.session import Session

from app.models import Exercise, Set, Workout


class WorkoutsRepository:
    def __init__(self, db: Session):
        self.db = db

    # Basic CRUD
    def get(self, id: int) -> Workout | None:
        return self.db.get(Workout, id)

    def list_(self, page: int, page_size: int = 10) -> list[Workout]:
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

    # Engine Tools

    def get_sets_for_metrics(
        self,
        exercise: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Set]:  # ORM Set objects, with workout + exercise reachable
        query = (
            select(Set)
            .join(Workout, Set.workout_id == Workout.id)
            .join(Exercise, Set.exercise_id == Exercise.id)
            .options(selectinload(Set.workout), selectinload(Set.exercise))
        )
        if exercise:
            query = query.where(Exercise.name == exercise)
        if start_date:
            query = query.where(Workout.performed_at >= start_date)
        if end_date:
            query = query.where(Workout.performed_at <= end_date)
        return list(self.db.scalars(query))
