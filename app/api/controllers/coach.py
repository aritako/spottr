from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.handlers.coach import CoachHandler
from app.core.db import get_db
from app.shared.schemas.coach import AskRequest, AskResponse

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask_coach(
    db: Annotated[Session, Depends(get_db)],
    request: AskRequest,
) -> AskResponse:
    handler = CoachHandler(db)
    return handler.ask(request)
