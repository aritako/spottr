from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.enums.workouts import UnitEnum


# Mixins
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, onupdate=func.now()
    )


# Tables


class Exercise(Base):
    __tablename__ = "exercise"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    category: Mapped[str | None] = mapped_column(default=None)
    is_compound: Mapped[bool] = mapped_column(default=False)


class Workout(TimestampMixin, Base):
    __tablename__ = "workout"

    id: Mapped[int] = mapped_column(primary_key=True)
    notes: Mapped[str | None] = mapped_column(default=None)
    unit: Mapped[str] = mapped_column(default=UnitEnum.KG.value)
    bodyweight: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    sets: Mapped[list["Set"]] = relationship(back_populates="workout", cascade="all, delete-orphan")
    performed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class Set(TimestampMixin, Base):
    __tablename__ = "sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workout.id"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercise.id"))
    weight: Mapped[float] = mapped_column(Numeric(6, 2))
    reps: Mapped[int] = mapped_column(default=0)
    rpe: Mapped[float | None] = mapped_column(nullable=True)
    set_index: Mapped[int] = mapped_column(default=0)
    workout: Mapped["Workout"] = relationship(back_populates="sets")
