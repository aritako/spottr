from fastapi.testclient import TestClient


def test_create_and_read_exercise(client: TestClient) -> None:
    create = client.post(
        "/exercises",
        json={"name": "Back Squat", "category": "squat", "is_compound": True},
    )
    assert create.status_code == 201, create.text
    exercise_id = create.json()["id"]

    read = client.get(f"/exercises/{exercise_id}")
    assert read.status_code == 200, read.text
    body = read.json()
    assert body["name"] == "Back Squat"
    assert body["category"] == "squat"
    assert body["is_compound"] is True


def test_list_exercises_returns_created(client: TestClient) -> None:
    client.post("/exercises", json={"name": "Bench Press"})
    client.post("/exercises", json={"name": "Deadlift"})

    listing = client.get("/exercises", params={"page": 0, "page_size": 10})
    assert listing.status_code == 200, listing.text
    names = {row["name"] for row in listing.json()}
    assert {"Bench Press", "Deadlift"} <= names


def test_read_missing_exercise_returns_404(client: TestClient) -> None:
    response = client.get("/exercises/999999")
    assert response.status_code == 404
