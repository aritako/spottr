from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def create_exercise(client: TestClient) -> Callable[..., int]:
    """Create an exercise through the API and return its id."""

    def _create(name: str = "Back Squat", **fields: object) -> int:
        response = client.post("/exercises", json={"name": name, **fields})
        assert response.status_code == 201, response.text
        return int(response.json()["id"])

    return _create
