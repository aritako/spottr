from fastapi.testclient import TestClient


def _create_exercise(client: TestClient, name: str = "Back Squat") -> int:
    response = client.post("/exercises", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _workout_payload(exercise_id: int) -> dict:
    return {
        "unit": "kg",
        "bodyweight": 80.5,
        "notes": "heavy day",
        "performed_at": "2026-10-26T12:00:00Z",
        "sets": [
            {"exercise_id": exercise_id, "weight": 100.0, "reps": 5},
            {"exercise_id": exercise_id, "weight": 102.5, "reps": 3, "rpe": 9.0},
        ],
    }


def test_create_workout_persists_sets_with_decimal_and_tz(client: TestClient) -> None:
    exercise_id = _create_exercise(client)

    create = client.post("/workouts", json=_workout_payload(exercise_id))
    assert create.status_code == 201, create.text
    workout_id = create.json()["id"]

    read = client.get(f"/workouts/{workout_id}")
    assert read.status_code == 200, read.text
    body = read.json()
    assert body["bodyweight"] == 80.5
    assert body["unit"] == "kg"
    assert len(body["sets"]) == 2
    assert sorted(s["set_index"] for s in body["sets"]) == [0, 1]
    assert {s["weight"] for s in body["sets"]} == {100.0, 102.5}
    # Timezone-aware round-trip: stored TIMESTAMPTZ must keep the instant.
    assert body["performed_at"].startswith("2026-10-26T12:00:00")


def test_create_workout_unknown_exercise_returns_404(client: TestClient) -> None:
    response = client.post("/workouts", json=_workout_payload(exercise_id=999999))
    assert response.status_code == 404, response.text


def test_delete_workout_cascades_sets(client: TestClient) -> None:
    exercise_id = _create_exercise(client)
    workout_id = client.post("/workouts", json=_workout_payload(exercise_id)).json()["id"]

    delete = client.delete(f"/workouts/{workout_id}")
    assert delete.status_code == 204, delete.text

    assert client.get(f"/workouts/{workout_id}").status_code == 404


def test_delete_missing_workout_returns_404(client: TestClient) -> None:
    assert client.delete("/workouts/999999").status_code == 404
