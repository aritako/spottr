from collections.abc import Generator

import pytest
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url
from sqlalchemy.orm import Session

from alembic import command as alembic_command
from app.core.config import settings
from app.core.db import get_db
from app.main import app

TEST_DATABASE_NAME = "coach_test"

_engine: Engine | None = None


def _test_database_url() -> str:
    """Return the isolated test DB URL, refusing to guess or fall back to dev."""
    url = settings.test_database_url
    if not url:
        pytest.exit("TEST_DATABASE_URL is not set; run `pnpm test:api`.", returncode=1)

    database = make_url(url).database
    if database != TEST_DATABASE_NAME:
        pytest.exit(
            f"TEST_DATABASE_URL must point at '{TEST_DATABASE_NAME}', not '{database}'.",
            returncode=1,
        )
    return url


def _test_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(_test_database_url(), pool_pre_ping=True)
    return _engine


@pytest.fixture(scope="session")
def _migrated_db() -> Generator[None, None, None]:
    """Run `alembic upgrade head` once per test session against the test DB."""
    cfg = AlembicConfig("alembic.ini")
    # str(url) masks the password as "***"; render it in full for the connection.
    url = _test_engine().url.render_as_string(hide_password=False)
    cfg.set_main_option("sqlalchemy.url", url)
    alembic_command.upgrade(cfg, "head")
    yield


@pytest.fixture(scope="function")
def db_session(_migrated_db: None) -> Generator[Session, None, None]:
    """Yield a session inside a rolled-back transaction (SAVEPOINT-safe)."""
    connection = _test_engine().connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

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
