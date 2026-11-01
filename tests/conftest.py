import os
from collections.abc import Generator

import pytest
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command as alembic_command
from app.core.config import settings
from app.core.db import get_db
from app.main import app


def _test_database_url() -> str:
    """Test DB URL: explicit TEST_DATABASE_URL wins, else the dev DATABASE_URL."""
    return settings.test_database_url or os.getenv("TEST_DATABASE_URL") or settings.database_url


engine = create_engine(_test_database_url(), pool_pre_ping=True)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    join_transaction_mode="create_savepoint",
)


@pytest.fixture(scope="session")
def _migrated_db() -> Generator[None, None, None]:
    """Run `alembic upgrade head` once per test session against the test DB."""
    cfg = AlembicConfig("alembic.ini")
    # str(url) masks the password as "***"; render it in full for the connection.
    cfg.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    alembic_command.upgrade(cfg, "head")
    yield


@pytest.fixture(scope="function")
def db_session(_migrated_db: None) -> Generator[Session, None, None]:
    """Yield a session inside a rolled-back transaction (SAVEPOINT-safe)."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with get_db overridden to use the transactional test session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
