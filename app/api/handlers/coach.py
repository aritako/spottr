from sqlalchemy.orm import Session

from app.engine.coach import Coach
from app.shared.schemas.coach import AskRequest, AskResponse


class CoachHandler:
    def __init__(self, db: Session):
        self.db = db

    def ask(self, request: AskRequest) -> AskResponse:
        coach = Coach(self.db)
        result = coach.ask_coach(request.question)
        return AskResponse(**result)
