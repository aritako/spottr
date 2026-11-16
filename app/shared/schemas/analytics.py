from datetime import datetime

from pydantic import BaseModel

from app.shared.enums.coach import Metric
from app.shared.enums.workouts import UnitEnum
from app.shared.metrics import GroupBy


class AnalyticsBucket(BaseModel):
    label: str
    value: float


class ExerciseSeriesRead(BaseModel):
    exercise_id: int
    metric: Metric
    group_by: GroupBy
    buckets: list[AnalyticsBucket]


class SessionSetRead(BaseModel):
    weight: float
    reps: int
    rpe: float | None
    set_index: int


class TopSetRead(BaseModel):
    weight: float
    reps: int


class ExerciseSessionRead(BaseModel):
    workout_id: int
    performed_at: datetime
    unit: UnitEnum
    sets: list[SessionSetRead]
    top_set: TopSetRead
    e1rm: float
    tonnage: float
