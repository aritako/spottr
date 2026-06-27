from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ExerciseCategory(StrEnum):
    SQUAT = "squat"  # back squat, front squat, goblet
    HINGE = "hinge"  # deadlift, RDL, hip thrust, KB swing
    LUNGE = "lunge"  # split squat, walking lunge, step-up
    HORIZONTAL_PUSH = "horizontal_push"  # bench, push-up
    VERTICAL_PUSH = "vertical_push"  # overhead press
    HORIZONTAL_PULL = "horizontal_pull"  # barbell/dumbbell row
    VERTICAL_PULL = "vertical_pull"  # pull-up, lat pulldown
    CARRY = "carry"  # farmer's carry, suitcase carry
    ISOLATION = "isolation"  # curls, lateral raises, leg ext, etc.
    CORE = "core"  # abs


class ExerciseCreate(BaseModel):
    name: str
    category: ExerciseCategory | None = None
    is_compound: bool = False


class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    category: ExerciseCategory | None = None
    is_compound: bool
