from pydantic import BaseModel, ConfigDict


class ExerciseCreate(BaseModel):
    name: str
    category: str | None = None
    is_compound: bool = False


class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    category: str | None = None
    is_compound: bool
