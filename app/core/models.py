from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.shared.enums.workouts import UnitEnum


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
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    category: Mapped[str | None] = mapped_column(default=None)
    is_compound: Mapped[bool] = mapped_column(default=False)
    sets: Mapped[list["Set"]] = relationship(back_populates="exercise")


class Workout(TimestampMixin, Base):
    __tablename__ = "workouts"

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
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    weight: Mapped[float] = mapped_column(Numeric(6, 2))
    reps: Mapped[int] = mapped_column(default=0)
    rpe: Mapped[float | None] = mapped_column(nullable=True)
    set_index: Mapped[int] = mapped_column(default=0)
    workout: Mapped["Workout"] = relationship(back_populates="sets")
    exercise: Mapped["Exercise"] = relationship(back_populates="sets")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    chunk_index: Mapped[int] = mapped_column()
    content: Mapped[str] = mapped_column()
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    document: Mapped["Document"] = relationship(back_populates="chunks")


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    source: Mapped[str | None] = mapped_column(default=None)
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
