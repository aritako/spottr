from sqlalchemy import Boolean, Column, Integer, String

from app.db import Base


class Exercise(Base):
    __tablename__ = "exercise"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, required=True)
    category = Column(String, nullable=True)
    is_compound = Column(Boolean, default=False)
