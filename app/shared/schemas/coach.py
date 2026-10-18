from pydantic import BaseModel


class Citation(BaseModel):
    document: str
    chunk_index: int


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    used_tools: list[str]
    citations: list[Citation]
