from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.shared.enums.docs import RetrievalStatus


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


class PassageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    document_title: str
    chunk_index: int
    content: str


class PassageRetrieval(BaseModel):
    status: RetrievalStatus
    passages: list[PassageRead]
