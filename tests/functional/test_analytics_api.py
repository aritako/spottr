from collections.abc import Iterable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from tests.functional.helpers import create_exercise

SetPayload = tuple[float, int, float | None, int | None]
OtherSetPayload = tuple[int, float, int]


def create_workout(
    client: TestClient,
    exercise_id: int,
    performed_at: str,
    sets: Iterable[SetPayload],
    unit: str = "kg",
    extra_sets: Iterable[OtherSetPayload] = (),
) -> int:
    """Create a workout through the API and return its id."""
    payload_sets = [
        {
            "exercise_id": exercise_id,
            "weight": weight,
            "reps": reps,
            "rpe": rpe,
            "set_index": set_index,
        }
        for weight, reps, rpe, set_index in sets
    ]
    payload_sets.extend(
        {"exercise_id": other_id, "weight": weight, "reps": reps}
        for other_id, weight, reps in extra_sets
    )
    response = client.post(
        "/workouts",
        json={
            "unit": unit,
            "performed_at": performed_at,
            "sets": payload_sets,
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _seed_series_workouts(client: TestClient, exercise_id: int) -> None:
    create_workout(
        client,
        exercise_id,
        "2026-06-15T12:00:00Z",
        [(100.0, 5, None, None), (120.0, 3, 9.0, None)],
    )
    create_workout(client, exercise_id, "2026-06-17T08:00:00Z", [(110.0, 4, None, None)])
    create_workout(client, exercise_id, "2026-07-01T18:00:00Z", [(130.0, 2, None, None)])


def test_series_defaults_to_weekly_tonnage(client: TestClient) -> None:
    exercise_id = create_exercise(client)
    _seed_series_workouts(client, exercise_id)

    response = client.get(f"/analytics/exercises/{exercise_id}/series")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "exercise_id": exercise_id,
        "metric": "tonnage",
        "group_by": "week",
        "buckets": [
            {"label": "Week of Jun 15, 2026", "value": 1300.0},
            {"label": "Week of Jun 29, 2026", "value": 260.0},
        ],
    }


@pytest.mark.parametrize(
    ("group_by", "expected"),
    [
        (
            "day",
            [
                {"label": "Jun 15, 2026", "value": 860.0},
                {"label": "Jun 17, 2026", "value": 440.0},
                {"label": "Jul 01, 2026", "value": 260.0},
            ],
        ),
        (
            "week",
            [
                {"label": "Week of Jun 15, 2026", "value": 1300.0},
                {"label": "Week of Jun 29, 2026", "value": 260.0},
            ],
        ),
        (
            "month",
            [
                {"label": "Jun 2026", "value": 1300.0},
                {"label": "Jul 2026", "value": 260.0},
            ],
        ),
        ("year", [{"label": "2026", "value": 1560.0}]),
    ],
)
def test_series_tonnage_for_every_group_by(
    client: TestClient, group_by: str, expected: list[dict[str, object]]
) -> None:
    exercise_id = create_exercise(client)
    _seed_series_workouts(client, exercise_id)

    response = client.get(
        f"/analytics/exercises/{exercise_id}/series",
        params={"metric": "tonnage", "group_by": group_by},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["metric"] == "tonnage"
    assert body["group_by"] == group_by
    assert body["buckets"] == expected


@pytest.mark.parametrize(
    ("group_by", "expected"),
    [
        (
            "day",
            [
                {"label": "Jun 15, 2026", "value": 132.0},
                {"label": "Jun 17, 2026", "value": 124.67},
                {"label": "Jul 01, 2026", "value": 138.67},
            ],
        ),
        (
            "week",
            [
                {"label": "Week of Jun 15, 2026", "value": 132.0},
                {"label": "Week of Jun 29, 2026", "value": 138.67},
            ],
        ),
        (
            "month",
            [
                {"label": "Jun 2026", "value": 132.0},
                {"label": "Jul 2026", "value": 138.67},
            ],
        ),
        ("year", [{"label": "2026", "value": 138.67}]),
    ],
)
def test_series_e1rm_keeps_the_bucket_maximum_for_every_group_by(
    client: TestClient, group_by: str, expected: list[dict[str, object]]
) -> None:
    exercise_id = create_exercise(client)
    _seed_series_workouts(client, exercise_id)

    response = client.get(
        f"/analytics/exercises/{exercise_id}/series",
        params={"metric": "e1rm", "group_by": group_by},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["metric"] == "e1rm"
    assert body["group_by"] == group_by
    assert body["buckets"] == expected


def test_series_end_date_is_inclusive(client: TestClient) -> None:
    exercise_id = create_exercise(client)
    create_workout(client, exercise_id, "2026-06-15T23:00:00Z", [(100.0, 5, None, None)])
    create_workout(client, exercise_id, "2026-06-16T23:59:00Z", [(110.0, 5, None, None)])
    create_workout(client, exercise_id, "2026-06-17T00:00:00Z", [(120.0, 5, None, None)])

    response = client.get(
        f"/analytics/exercises/{exercise_id}/series",
        params={
            "start_date": "2026-06-15",
            "end_date": "2026-06-16",
            "group_by": "day",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["buckets"] == [
        {"label": "Jun 15, 2026", "value": 500.0},
        {"label": "Jun 16, 2026", "value": 550.0},
    ]


def test_series_unknown_exercise_returns_404(client: TestClient) -> None:
    response = client.get("/analytics/exercises/999999/series")

    assert response.status_code == 404, response.text


def test_series_returns_an_empty_bucket_list_when_the_range_has_no_data(
    client: TestClient,
) -> None:
    exercise_id = create_exercise(client)

    response = client.get(
        f"/analytics/exercises/{exercise_id}/series",
        params={"start_date": "2030-01-01", "end_date": "2030-12-31"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "exercise_id": exercise_id,
        "metric": "tonnage",
        "group_by": "week",
        "buckets": [],
    }


def test_sessions_returns_per_workout_rows_newest_first(client: TestClient) -> None:
    exercise_id = create_exercise(client)
    other_id = create_exercise(client, name="Bench Press")
    older_id = create_workout(
        client,
        exercise_id,
        "2026-06-15T12:00:00Z",
        [(150.0, 10, 8.0, 2), (100.0, 30, None, 1), (120.0, 5, 9.0, 3)],
        extra_sets=[(other_id, 999.0, 1)],
    )
    newer_id = create_workout(
        client, exercise_id, "2026-06-20T09:30:00Z", [(200.0, 3, None, None)], unit="lbs"
    )

    response = client.get(f"/analytics/exercises/{exercise_id}/sessions")

    assert response.status_code == 200, response.text
    rows = response.json()
    assert [row["workout_id"] for row in rows] == [newer_id, older_id]

    newer = rows[0]
    assert newer["unit"] == "lbs"
    assert newer["sets"] == [{"weight": 200.0, "reps": 3, "rpe": None, "set_index": 0}]
    assert newer["top_set"] == {"weight": 200.0, "reps": 3}
    assert newer["e1rm"] == 220.0
    assert newer["tonnage"] == 600.0
    performed_at = datetime.fromisoformat(newer["performed_at"].replace("Z", "+00:00"))
    assert performed_at == datetime(2026, 6, 20, 9, 30, tzinfo=UTC)

    older = rows[1]
    assert older["unit"] == "kg"
    assert older["sets"] == [
        {"weight": 100.0, "reps": 30, "rpe": None, "set_index": 1},
        {"weight": 150.0, "reps": 10, "rpe": 8.0, "set_index": 2},
        {"weight": 120.0, "reps": 5, "rpe": 9.0, "set_index": 3},
    ]
    # The 150x10 and 100x30 sets tie on e1RM; the earliest set_index wins.
    assert older["top_set"] == {"weight": 100.0, "reps": 30}
    assert older["e1rm"] == 200.0
    # Only the requested exercise's sets count toward the row tonnage.
    assert older["tonnage"] == 5100.0


def test_sessions_paginate_newest_first(client: TestClient) -> None:
    exercise_id = create_exercise(client)
    first = create_workout(client, exercise_id, "2026-06-15T12:00:00Z", [(100.0, 5, None, None)])
    second = create_workout(client, exercise_id, "2026-06-16T12:00:00Z", [(100.0, 5, None, None)])
    third = create_workout(client, exercise_id, "2026-06-17T12:00:00Z", [(100.0, 5, None, None)])

    first_page = client.get(
        f"/analytics/exercises/{exercise_id}/sessions", params={"page": 0, "page_size": 2}
    )
    second_page = client.get(
        f"/analytics/exercises/{exercise_id}/sessions", params={"page": 1, "page_size": 2}
    )

    assert first_page.status_code == 200, first_page.text
    assert [row["workout_id"] for row in first_page.json()] == [third, second]
    assert second_page.status_code == 200, second_page.text
    assert [row["workout_id"] for row in second_page.json()] == [first]


def test_sessions_end_date_is_inclusive(client: TestClient) -> None:
    exercise_id = create_exercise(client)
    on_end_date = create_workout(
        client, exercise_id, "2026-06-16T23:59:00Z", [(100.0, 5, None, None)]
    )
    before_end_date = create_workout(
        client, exercise_id, "2026-06-15T23:00:00Z", [(100.0, 5, None, None)]
    )
    create_workout(client, exercise_id, "2026-06-17T00:00:00Z", [(100.0, 5, None, None)])

    response = client.get(
        f"/analytics/exercises/{exercise_id}/sessions",
        params={"start_date": "2026-06-15", "end_date": "2026-06-16"},
    )

    assert response.status_code == 200, response.text
    assert [row["workout_id"] for row in response.json()] == [on_end_date, before_end_date]


def test_sessions_unknown_exercise_returns_404(client: TestClient) -> None:
    response = client.get("/analytics/exercises/999999/sessions")

    assert response.status_code == 404, response.text


def test_sessions_returns_an_empty_list_when_the_range_has_no_data(
    client: TestClient,
) -> None:
    exercise_id = create_exercise(client)

    response = client.get(
        f"/analytics/exercises/{exercise_id}/sessions",
        params={"start_date": "2030-01-01", "end_date": "2030-12-31"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == []
