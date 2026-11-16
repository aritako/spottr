from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.session import Session

from app.core.models import Set, Workout


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

    def delete(self, workout: Workout) -> None:
        try:
            self.db.delete(workout)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    # Analytics

    def get_sets_for_exercise(
        self,
        exercise_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Set]:
        query = (
            select(Set)
            .join(Workout, Set.workout_id == Workout.id)
            .where(Set.exercise_id == exercise_id)
            .options(selectinload(Set.workout))
            .order_by(Workout.performed_at, Set.set_index, Set.id)
        )
        if start_date:
            query = query.where(Workout.performed_at >= start_date)
        if end_date:
            query = query.where(Workout.performed_at < end_date + timedelta(days=1))
        return list(self.db.scalars(query))

    def list_workouts_for_exercise(
        self,
        exercise_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 0,
        page_size: int = 10,
    ) -> list[Workout]:
        query = (
            select(Workout)
            .join(Set, Set.workout_id == Workout.id)
            .where(Set.exercise_id == exercise_id)
            .distinct()
            .order_by(Workout.performed_at.desc(), Workout.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        if start_date:
            query = query.where(Workout.performed_at >= start_date)
        if end_date:
            query = query.where(Workout.performed_at < end_date + timedelta(days=1))
        return list(self.db.scalars(query))

    def get_sets_for_workouts(self, workout_ids: list[int], exercise_id: int) -> list[Set]:
        if not workout_ids:
            return []
        query = (
            select(Set)
            .where(Set.exercise_id == exercise_id, Set.workout_id.in_(workout_ids))
            .options(selectinload(Set.workout))
            .order_by(Set.set_index, Set.id)
        )
        return list(self.db.scalars(query))

    # Analytics across all exercises

    def get_sets_for_all_exercises(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Set]:  # ORM Set objects, with workout + exercise reachable
        query = (
            select(Set)
            .join(Workout, Set.workout_id == Workout.id)
            .options(selectinload(Set.workout), selectinload(Set.exercise))
        )
        if start_date:
            query = query.where(Workout.performed_at >= start_date)
        if end_date:
            query = query.where(Workout.performed_at < end_date + timedelta(days=1))
        return list(self.db.scalars(query))
