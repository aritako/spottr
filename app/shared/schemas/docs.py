from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.shared.enums.docs import SearchStatus


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
    document_id: int
    document: str
    chunk_index: int
    content: str


class PassageSearch(BaseModel):
    status: SearchStatus
    results: list[PassageRead]
