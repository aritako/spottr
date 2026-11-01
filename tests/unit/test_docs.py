from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.api.handlers.docs import DocsHandler
from app.core.models import Document
from app.shared.errors.docs import EmptyDocumentError
from app.shared.schemas.docs import DocumentRead


def _handler() -> DocsHandler:
    return DocsHandler(MagicMock())


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
    embed.assert_called_once()
    document = create.call_args.args[0]
    assert len(document.chunks) == 1
    assert document.chunks[0].chunk_index == 0
    assert document.chunks[0].content == "deload every few weeks"


def test_ingest_empty_text_raises() -> None:
    handler = _handler()
    with pytest.raises(EmptyDocumentError):
        handler.ingest("Empty", None, "   ")
