from fastapi import FastAPI

from app.api.controllers import coach, exercises, workouts

app = FastAPI(title="Spottr", description="An AI-powered lifting coach", version="0.1.0")

app.include_router(exercises.router, prefix="/exercises", tags=["Exercise"])
app.include_router(workouts.router, prefix="/workouts", tags=["Workout"])
app.include_router(coach.router, prefix="/coach", tags=["Coach"])


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello, World!"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
