from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.api.handlers.docs import DocsHandler
from app.core.models import Chunk, Document
from app.engine.rag import (
    DEFAULT_TOP_K,
    DUPLICATE_OVERFETCH,
    EMBEDDING_DIMENSIONS,
    MAX_COSINE_DISTANCE,
    MAX_TOP_K,
    MIN_TOP_K,
)
from app.shared.enums.docs import RetrievalStatus
from app.shared.errors.docs import EmbeddingDimensionError, EmptyDocumentError
from app.shared.schemas.docs import DocumentRead


def _handler() -> DocsHandler:
    return DocsHandler(MagicMock())


def _chunk(
    document_id: int = 1,
    title: str = "Deload Guidelines",
    chunk_index: int = 0,
    content: str = "Deload every four to six weeks when performance stalls.",
) -> Chunk:
    chunk = Chunk(document_id=document_id, chunk_index=chunk_index, content=content)
    chunk.document = Document(id=document_id, title=title)
    return chunk


@contextmanager
def _retrieval(
    handler: DocsHandler,
    chunks: list[Chunk] | None = None,
    has_chunks: bool = True,
    embedding: list[float] | None = None,
) -> Iterator[SimpleNamespace]:
    """Stub the embedding call and the repository behind DocsHandler.search."""
    vector = embedding if embedding is not None else [0.1] * EMBEDDING_DIMENSIONS
    with (
        patch("app.api.handlers.docs.get_embeddings", return_value=[vector]) as embed,
        patch.object(handler.repository, "retrieve", return_value=chunks or []) as retrieve,
        patch.object(handler.repository, "has_chunks", return_value=has_chunks) as has_chunks_mock,
    ):
        yield SimpleNamespace(embed=embed, retrieve=retrieve, has_chunks=has_chunks_mock)


def test_ingest_builds_chunks_from_text() -> None:
    handler = _handler()
    created = Document(id=1, title="Deload", source="deload.md")
    created.created_at = datetime.now(UTC)

    with (
        patch("app.api.handlers.docs.get_embeddings", return_value=[[0.5] * 1536]) as embed,
        patch.object(handler.repository, "create", return_value=created) as create,
    ):
        result = handler.ingest("Deload", "deload.md", "deload every few weeks")

    assert result == DocumentRead.model_validate(created)
    embed.assert_called_once_with(["Deload\n\ndeload every few weeks"])
    document = create.call_args.args[0]
    assert len(document.chunks) == 1
    assert document.chunks[0].chunk_index == 0
    assert document.chunks[0].content == "deload every few weeks"


def test_ingest_empty_text_raises() -> None:
    handler = _handler()
    with pytest.raises(EmptyDocumentError):
        handler.ingest("Empty", None, "   ")


def test_retrieve_returns_passages_from_retrieved_chunks() -> None:
    handler = _handler()
    chunk = _chunk(chunk_index=2)

    with _retrieval(handler, chunks=[chunk]) as stubs:
        result = handler.retrieve("should I deload?")

    stubs.embed.assert_called_once_with(["should I deload?"])
    assert stubs.retrieve.call_args.args == (
        [0.1] * EMBEDDING_DIMENSIONS,
        DEFAULT_TOP_K * DUPLICATE_OVERFETCH,
        MAX_COSINE_DISTANCE,
    )
    assert result.status == RetrievalStatus.OK
    assert [passage.model_dump() for passage in result.passages] == [
        {
            "document_id": 1,
            "document_title": "Deload Guidelines",
            "chunk_index": 2,
            "content": "Deload every four to six weeks when performance stalls.",
        }
    ]


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(None, DEFAULT_TOP_K), (0, MIN_TOP_K), (3, 3), (MAX_TOP_K, MAX_TOP_K), (500, MAX_TOP_K)],
)
def test_retrieve_clamps_requested_passage_count(requested: int | None, expected: int) -> None:
    handler = _handler()

    with _retrieval(handler) as stubs:
        handler.retrieve("should I deload?", requested)

    assert stubs.retrieve.call_args.args[1] == expected * DUPLICATE_OVERFETCH


def test_retrieve_reports_no_match_when_nothing_is_close_enough() -> None:
    handler = _handler()

    with _retrieval(handler, has_chunks=True):
        result = handler.retrieve("how do I run a marathon?")

    assert result.status == RetrievalStatus.NO_MATCH
    assert result.passages == []


def test_retrieve_reports_empty_corpus_without_embedding_the_question() -> None:
    handler = _handler()

    with _retrieval(handler, has_chunks=False) as stubs:
        result = handler.retrieve("should I deload?")

    assert result.status == RetrievalStatus.EMPTY_CORPUS
    assert result.passages == []
    stubs.embed.assert_not_called()


def test_retrieve_requests_extra_candidates_to_backfill_duplicates() -> None:
    handler = _handler()
    repeated = "Deload when performance stalls."
    chunks = [
        _chunk(document_id=1, content=repeated),
        _chunk(document_id=2, title="Deload Guidelines (copy)", content=repeated),
        _chunk(document_id=3, title="RPE", content="Use RPE to autoregulate."),
    ]

    with _retrieval(handler, chunks=chunks) as stubs:
        result = handler.retrieve("should I deload?", 2)

    assert stubs.retrieve.call_args.args[1] == 2 * DUPLICATE_OVERFETCH
    assert [passage.document_id for passage in result.passages] == [1, 3]


def test_retrieve_rejects_an_embedding_of_the_wrong_dimension() -> None:
    handler = _handler()

    with (
        _retrieval(handler, embedding=[0.1] * (EMBEDDING_DIMENSIONS - 1)) as stubs,
        pytest.raises(EmbeddingDimensionError),
    ):
        handler.retrieve("should I deload?")

    stubs.retrieve.assert_not_called()
