from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.enums.workouts import UnitEnum


class SetCreate(BaseModel):
    exercise_id: int
    weight: float = Field(ge=0)
    reps: int = Field(ge=0)
    rpe: float | None = Field(default=None, ge=0, le=10)
    set_index: int | None = None


class WorkoutCreate(BaseModel):
    unit: UnitEnum
    bodyweight: float | None = Field(default=None, ge=0)
    notes: str | None = None
    performed_at: datetime
    sets: list[SetCreate]


class SetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exercise_id: int
    weight: float
    reps: int
    rpe: float | None
    set_index: int


class WorkoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit: UnitEnum
    bodyweight: float | None
    notes: str | None
    performed_at: datetime
    created_at: datetime
    sets: list[SetRead]
