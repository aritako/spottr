"""Seed the development database with sample exercises and workouts.

Run from the repository root:

    python scripts/seed.py            # seed only if the DB is empty
    python scripts/seed.py --reset    # wipe exercises/workouts, then reseed

The script reads ``DATABASE_URL`` through the app's settings, so point it at the
same database the API uses. Inside Docker:

    docker compose exec app python scripts/seed.py

or from the host (the ``db`` service publishes port 5432):

    DATABASE_URL=postgresql+psycopg://coach:coach@localhost:5432/coach \
        python scripts/seed.py
"""

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Make `app` importable when this script is run directly from the repo root,
# without relying on an installed package or PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.models import Exercise, Set, Workout  # noqa: E402
from app.shared.enums.exercises import ExerciseCategory  # noqa: E402
from app.shared.enums.workouts import UnitEnum  # noqa: E402

# (name, category, is_compound)
EXERCISES: list[tuple[str, ExerciseCategory, bool]] = [
    ("Back Squat", ExerciseCategory.SQUAT, True),
    ("Bench Press", ExerciseCategory.HORIZONTAL_PUSH, True),
    ("Deadlift", ExerciseCategory.HINGE, True),
    ("Overhead Press", ExerciseCategory.VERTICAL_PUSH, True),
    ("Barbell Row", ExerciseCategory.HORIZONTAL_PULL, True),
]

WEEKS = 12
SESSIONS_PER_WEEK = 3

# 3-day split: (main lift, accessory) per session.
SESSION_PLAN: list[tuple[str, str]] = [
    ("Back Squat", "Barbell Row"),
    ("Bench Press", "Overhead Press"),
    ("Deadlift", "Barbell Row"),
]

# Starting work weight and linear weekly progression (kg) for each exercise.
START_WEIGHT: dict[str, float] = {
    "Back Squat": 100.0,
    "Bench Press": 70.0,
    "Deadlift": 120.0,
    "Overhead Press": 40.0,
    "Barbell Row": 60.0,
}
WEEKLY_INCREMENT: dict[str, float] = {
    "Back Squat": 2.5,
    "Bench Press": 1.5,
    "Deadlift": 3.0,
    "Overhead Press": 1.0,
    "Barbell Row": 1.5,
}


def _sets(exercise_id: int, weight: float, reps: int, count: int, rpe: float) -> list[Set]:
    """Build ``count`` identical sets for one exercise."""
    return [
        Set(exercise_id=exercise_id, weight=weight, reps=reps, rpe=rpe, set_index=i)
        for i in range(count)
    ]


def _build_workouts(exercise_ids: dict[str, int]) -> list[Workout]:
    """Generate ``WEEKS`` weeks of progressive training, ending today."""
    workouts: list[Workout] = []
    anchor = datetime.now(UTC).replace(hour=18, minute=0, second=0, microsecond=0)

    for week in range(WEEKS):
        weeks_ago = WEEKS - 1 - week
        for session, (main, accessory) in enumerate(SESSION_PLAN):
            performed_at = anchor - timedelta(weeks=weeks_ago, days=2 - session)
            main_weight = START_WEIGHT[main] + WEEKLY_INCREMENT[main] * week
            accessory_weight = START_WEIGHT[accessory] + WEEKLY_INCREMENT[accessory] * week

            sets = _sets(exercise_ids[main], main_weight, reps=5, count=5, rpe=8.0)
            sets += _sets(exercise_ids[accessory], accessory_weight, reps=8, count=3, rpe=7.5)
            workouts.append(
                Workout(
                    unit=UnitEnum.KG.value,
                    bodyweight=82.5,
                    performed_at=performed_at,
                    sets=sets,
                )
            )
    return workouts


def seed(reset: bool = False) -> None:
    """Create exercises and workouts, optionally wiping existing data first."""
    with SessionLocal() as db:
        has_data = db.scalar(select(Exercise.id).limit(1)) is not None
        if has_data and not reset:
            print("Database already seeded; pass --reset to wipe and reseed.")
            return

        if reset:
            # FK-safe order: sets reference both workouts and exercises.
            db.execute(delete(Set))
            db.execute(delete(Workout))
            db.execute(delete(Exercise))
            db.commit()

        exercise_ids: dict[str, int] = {}
        for name, category, is_compound in EXERCISES:
            exercise = Exercise(name=name, category=category, is_compound=is_compound)
            db.add(exercise)
            db.flush()  # populate exercise.id before building sets
            exercise_ids[name] = exercise.id

        workouts = _build_workouts(exercise_ids)
        db.add_all(workouts)
        db.commit()

        print(f"Seeded {len(EXERCISES)} exercises and {len(workouts)} workouts.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the development database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="wipe exercises and workouts before seeding",
    )
    args = parser.parse_args()
    seed(reset=args.reset)


if __name__ == "__main__":
    main()
