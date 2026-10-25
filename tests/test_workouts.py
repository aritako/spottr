from unittest.mock import MagicMock, patch

import pytest

from app.api.handlers.workouts import WorkoutsHandler
from app.core.models import Workout
from app.shared.errors.workouts import WorkoutNotFoundError


def _handler() -> WorkoutsHandler:
    return WorkoutsHandler(MagicMock())


def test_delete_workout_deletes_when_found() -> None:
    handler = _handler()
    workout = Workout(id=1)

    with (
        patch.object(handler.workoutsRepository, "get", return_value=workout),
        patch.object(handler.workoutsRepository, "delete") as delete,
    ):
        handler.delete_workout(1)

    delete.assert_called_once_with(workout)


def test_delete_workout_not_found_raises() -> None:
    handler = _handler()

    with patch.object(handler.workoutsRepository, "get", return_value=None):
        with pytest.raises(WorkoutNotFoundError):
            handler.delete_workout(1)
