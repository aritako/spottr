from datetime import date
from unittest.mock import Mock

import pytest

from app.engine.helpers import DatedTonnageByExercise, weekly_tonnage_by_exercise


def test_weekly_tonnage_by_exercise() -> None:
    entries = [
        DatedTonnageByExercise(exercise="bench", date=date(2025, 12, 30), tonnage=100.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 1), tonnage=100.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 2), tonnage=120.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 8), tonnage=120.0),
        DatedTonnageByExercise(exercise="squat", date=date(2026, 1, 1), tonnage=80.0),
        DatedTonnageByExercise(exercise="squat", date=date(2026, 1, 8), tonnage=90.0),
        DatedTonnageByExercise(exercise="deadlift", date=date(2026, 1, 1), tonnage=150.0),
        DatedTonnageByExercise(exercise="deadlift", date=date(2026, 1, 8), tonnage=160.0),
        DatedTonnageByExercise(exercise="overhead press", date=date(2026, 1, 1), tonnage=100.0),
        DatedTonnageByExercise(exercise="overhead press", date=date(2026, 1, 8), tonnage=120.0),
    ]
    result = weekly_tonnage_by_exercise(entries)
    assert result == {
        "bench": [("2026-W01", 320.0), ("2026-W02", 120.0)],
        "squat": [("2026-W01", 80.0), ("2026-W02", 90.0)],
        "deadlift": [("2026-W01", 150.0), ("2026-W02", 160.0)],
        "overhead press": [("2026-W01", 100.0), ("2026-W02", 120.0)],
    }
