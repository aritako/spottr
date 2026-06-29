from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Set, Workout
from app.repository.workouts import WorkoutsRepository
from app.schemas.workouts import WorkoutCreate, WorkoutRead


class WorkoutsHandler:
    def __init__(self, db: Session):
        self.repository = WorkoutsRepository(db)

    def read_workout(self, id: int) -> WorkoutRead | None:
        workout = self.repository.get(id)
        if workout:
            return WorkoutRead.model_validate(workout)
        raise HTTPException(status_code=404, detail="Workout not found")

    def read_workout_list(self, page: int, page_size: int) -> list[WorkoutRead]:
        workouts = self.repository.list(page, page_size)
        return [WorkoutRead.model_validate(workout) for workout in workouts]

    def create_workout(self, workout: WorkoutCreate) -> WorkoutRead:
        setModelList = [
            Set(
                exercise_id=set.exercise_id,
                weight=set.weight,
                reps=set.reps,
                rpe=set.rpe,
                set_index=set.set_index if set.set_index else idx,
            )
            for idx, set in enumerate(workout.sets)
        ]
        workoutModel = Workout(
            unit=workout.unit,
            bodyweight=workout.bodyweight,
            notes=workout.notes,
            performed_at=workout.performed_at,
            sets=setModelList,
        )
        self.repository.create(workoutModel)
        return WorkoutRead.model_validate(workoutModel)
