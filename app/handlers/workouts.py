from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.errors.exercises import ExerciseNotFoundError
from app.models import Set, Workout
from app.repository.exercises import ExercisesRepository
from app.repository.workouts import WorkoutsRepository
from app.schemas.workouts import SetRead, WorkoutCreate, WorkoutRead


class WorkoutsHandler:
    def __init__(self, db: Session):
        self.workoutsRepository = WorkoutsRepository(db)
        self.exercisesRepository = ExercisesRepository(db)

    def create_workout(self, workout: WorkoutCreate) -> WorkoutRead:
        exercise_ids = {s.exercise_id for s in workout.sets}
        existing_ids = self.exercisesRepository.check(exercise_ids)
        missing_ids = exercise_ids - existing_ids

        if missing_ids:
            raise ExerciseNotFoundError()

        set_model_list = [
            Set(
                exercise_id=set.exercise_id,
                weight=set.weight,
                reps=set.reps,
                rpe=set.rpe,
                set_index=set.set_index if set.set_index else idx,
            )
            for idx, set in enumerate(workout.sets)
        ]
        workout_model = Workout(
            unit=workout.unit,
            bodyweight=workout.bodyweight,
            notes=workout.notes,
            performed_at=workout.performed_at,
            sets=set_model_list,
        )
        new_workout = self.workoutsRepository.create(workout_model)
        return WorkoutRead.model_validate(new_workout)

    def read_workout(self, id: int) -> WorkoutRead | None:
        workout = self.workoutsRepository.get(id)
        if workout:
            return WorkoutRead.model_validate(workout)
        raise HTTPException(status_code=404, detail="Workout not found")

    def read_workout_list(self, page: int, page_size: int) -> list[WorkoutRead]:
        workouts = self.workoutsRepository.list_(page, page_size)
        return [WorkoutRead.model_validate(workout) for workout in workouts]

    def get_sets_for_metrics(
        self, exercise: str | None, start: date | None, end: date | None
    ) -> list[SetRead]:
        sets = self.workoutsRepository.get_sets_for_metrics(exercise, start, end)
        return [SetRead.model_validate(set) for set in sets]
