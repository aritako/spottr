from app.core.db import SessionLocal
from app.engine.coach import Coach

db = SessionLocal()
try:
    coach = Coach(db)
    print(
        coach.ask_coach(
            """
            For the past few days, how is my e1rm? Is it progressing as expected?
            """
        )
    )
finally:
    db.close()
