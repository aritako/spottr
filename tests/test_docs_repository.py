from typing import Any, cast
from unittest.mock import MagicMock

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.api.repository.docs import DocsRepository
from app.engine.rag import MAX_COSINE_DISTANCE

# These tests read the compiled statement instead of executing it, because the transactional
# fixture needs a live pgvector database and the suite is mock-based until tests get their own
# container. They lock the two properties mocks otherwise can't: ascending cosine distance and
# the cutoff living in SQL rather than in Python.


class _Rows:
    """Stand-in for a SQLAlchemy Result holding (chunk, distance) tuples."""

    def __init__(self, rows: list[tuple[Any, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Any, Any]]:
        return self._rows


class _CapturingSession:
    """Stand-in for a Session that records the statement instead of executing it."""

    def __init__(self, rows: list[tuple[Any, Any]] | None = None) -> None:
        self.statement: Any = None
        self.rows = _Rows(rows or [])

    def execute(self, statement: Any) -> _Rows:
        self.statement = statement
        return self.rows

    def scalar(self, statement: Any) -> bool:
        self.statement = statement
        return False


def _repository(session: _CapturingSession) -> DocsRepository:
    return DocsRepository(cast(Session, session))


def _compiled(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def test_retrieve_orders_by_ascending_cosine_distance() -> None:
    session = _CapturingSession()

    _repository(session).retrieve([0.1] * 3, k=5, max_distance=MAX_COSINE_DISTANCE)

    sql = _compiled(session.statement)
    assert "chunks.embedding <=> " in sql
    assert "ORDER BY" in sql
    assert "DESC" not in sql
    assert "LIMIT" in sql


def test_retrieve_applies_the_distance_cutoff_in_sql() -> None:
    session = _CapturingSession()

    _repository(session).retrieve([0.1] * 3, k=5, max_distance=0.42)

    where_clause = _compiled(session.statement).split("WHERE", 1)[1].split("ORDER BY", 1)[0]
    assert "chunks.embedding <=>" in where_clause
    assert 0.42 in session.statement.compile().params.values()


def test_retrieve_returns_chunks_paired_with_their_distance() -> None:
    chunk = MagicMock()
    session = _CapturingSession([(chunk, 0.31)])

    assert _repository(session).retrieve([0.1] * 3, k=5, max_distance=MAX_COSINE_DISTANCE) == [
        (chunk, 0.31)
    ]


def test_has_chunks_reports_whether_any_chunk_exists() -> None:
    session = _CapturingSession()
    session.scalar = lambda statement: True

    assert _repository(session).has_chunks() is True
