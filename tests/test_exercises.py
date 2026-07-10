from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_exercises() -> None:
    # TODO: We need setup for a test db and transactional rollback per test.
