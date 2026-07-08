from app.db import SessionLocal
from app.engine.coach import Coach

db = SessionLocal()
try:
    coach = Coach(db)
    print(coach.ask_coach("Based on my squat weekly tonnage, what should I aim for next week?"))
finally:
    db.close()
