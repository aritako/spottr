from collections.abc import Callable

from fastapi.testclient import TestClient


def test_create_and_read_exercise(client: TestClient, create_exercise: Callable[..., int]) -> None:
    exercise_id = create_exercise("Back Squat", category="squat", is_compound=True)

    read = client.get(f"/exercises/{exercise_id}")
    assert read.status_code == 200, read.text
    body = read.json()
    assert body["name"] == "Back Squat"
    assert body["category"] == "squat"
    assert body["is_compound"] is True


def test_list_exercises_returns_created(
    client: TestClient, create_exercise: Callable[..., int]
) -> None:
    create_exercise("Bench Press")
    create_exercise("Deadlift")

    listing = client.get("/exercises", params={"page": 0, "page_size": 10})
    assert listing.status_code == 200, listing.text
    names = {row["name"] for row in listing.json()}
    assert {"Bench Press", "Deadlift"} <= names


def test_read_missing_exercise_returns_404(client: TestClient) -> None:
    response = client.get("/exercises/999999")
    assert response.status_code == 404
