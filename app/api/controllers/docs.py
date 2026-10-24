from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm.session import Session

from app.api.handlers.docs import DocsHandler
from app.core.db import get_db
from app.shared.errors.docs import EmptyDocumentError
from app.shared.schemas.docs import DocumentIngest, DocumentRead, DocumentReadResponse

router = APIRouter()


@router.get("", response_model=list[DocumentRead])
def get_documents(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(0, ge=0),
    page_size: int = Query(10, ge=1, le=100),
) -> list[DocumentRead]:
    handler = DocsHandler(db)
    return handler.read_document_list(page, page_size)


@router.post("/ingest", status_code=201, response_model=DocumentReadResponse)
def ingest_document(
    db: Annotated[Session, Depends(get_db)],
    payload: DocumentIngest,
) -> DocumentReadResponse:
    handler = DocsHandler(db)
    try:
        document = handler.ingest(payload.title, payload.source, payload.text)
    except EmptyDocumentError as e:
        raise HTTPException(status_code=400, detail="Document text is empty.") from e
    return DocumentReadResponse(id=document.id)
