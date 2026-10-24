from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentIngest(BaseModel):
    title: str
    source: str | None = None
    text: str


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source: str | None
    created_at: datetime


class DocumentReadResponse(BaseModel):
    id: int
