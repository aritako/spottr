from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.enums.exercises import ExerciseCategory


class ExerciseCreate(BaseModel):
    name: str
    category: ExerciseCategory | None = None
    is_compound: bool = False


class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: ExerciseCategory | None = None
    is_compound: bool


class ExerciseReadResponse(BaseModel):
    id: int
