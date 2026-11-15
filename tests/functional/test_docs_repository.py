from sqlalchemy.orm import Session

from app.api.repository.docs import DocsRepository
from app.core.models import Chunk, Document

DIMENSIONS = 1536
QUERY = [1.0] + [0.0] * (DIMENSIONS - 1)


def _deload_document() -> Document:
    """A document whose two chunks point in orthogonal directions from the query."""
    return Document(
        title="Deload Guidelines",
        chunks=[
            Chunk(
                chunk_index=0,
                content="Deload when performance stalls.",
                embedding=[0.0, 1.0] + [0.0] * (DIMENSIONS - 2),
            ),
            Chunk(
                chunk_index=1,
                content="Keep intensity, cut volume.",
                embedding=[1.0] + [0.0] * (DIMENSIONS - 1),
            ),
        ],
    )


def test_retrieve_orders_the_closest_chunk_first(db_session: Session) -> None:
    db_session.add(_deload_document())
    db_session.flush()

    chunks = DocsRepository(db_session).retrieve(QUERY, k=5, max_distance=2.0)

    assert [chunk.content for chunk in chunks] == [
        "Keep intensity, cut volume.",
        "Deload when performance stalls.",
    ]


def test_retrieve_drops_chunks_beyond_the_cutoff(db_session: Session) -> None:
    db_session.add(_deload_document())
    db_session.flush()

    chunks = DocsRepository(db_session).retrieve(QUERY, k=5, max_distance=0.5)

    assert [chunk.chunk_index for chunk in chunks] == [1]


def test_retrieve_exposes_each_chunks_document_title(db_session: Session) -> None:
    db_session.add(_deload_document())
    db_session.flush()

    chunks = DocsRepository(db_session).retrieve(QUERY, k=5, max_distance=2.0)

    assert [chunk.document_title for chunk in chunks] == [
        "Deload Guidelines",
        "Deload Guidelines",
    ]


def test_has_chunks_is_false_before_anything_is_ingested(db_session: Session) -> None:
    repository = DocsRepository(db_session)

    assert repository.has_chunks() is False

    db_session.add(_deload_document())
    db_session.flush()

    assert repository.has_chunks() is True


def test_list_chunks_returns_every_chunk_with_its_document(db_session: Session) -> None:
    rpe = Document(
        title="RPE Guide",
        source="rpe.md",
        chunks=[
            Chunk(
                chunk_index=0,
                content="RPE 8 is about two reps left.",
                embedding=[0.0, 1.0] + [0.0] * (DIMENSIONS - 2),
            )
        ],
    )
    db_session.add_all([_deload_document(), rpe])
    db_session.flush()

    chunks = DocsRepository(db_session).list_chunks()

    assert len(chunks) == 3
    assert all(chunk.document is not None for chunk in chunks)
    assert [chunk.document.title for chunk in chunks] == [
        "Deload Guidelines",
        "Deload Guidelines",
        "RPE Guide",
    ]
