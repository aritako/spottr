from fastapi.testclient import TestClient


def create_exercise(client: TestClient, name: str = "Back Squat", **fields: object) -> int:
    """Create an exercise through the API and return its id."""
    response = client.post("/exercises", json={"name": name, **fields})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])
