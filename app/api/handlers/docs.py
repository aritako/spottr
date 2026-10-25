from sqlalchemy.orm import Session

from app.api.repository.docs import DocsRepository
from app.core.models import Chunk, Document
from app.engine.rag import (
    DUPLICATE_OVERFETCH,
    EMBEDDING_DIMENSIONS,
    MAX_COSINE_DISTANCE,
    chunk_text,
    get_embeddings,
    normalize_k,
)
from app.shared.enums.docs import SearchStatus
from app.shared.errors.docs import EmbeddingDimensionError, EmptyDocumentError
from app.shared.schemas.docs import DocumentRead, PassageRead, PassageSearch


class DocsHandler:
    def __init__(self, db: Session):
        self.repository = DocsRepository(db)

    def ingest(self, title: str, source: str | None, text: str) -> DocumentRead:
        chunks = chunk_text(text)
        if not chunks:
            raise EmptyDocumentError()

        embeddings = get_embeddings(chunks)
        document = Document(
            title=title,
            source=source,
            chunks=[
                Chunk(chunk_index=index, content=content, embedding=embedding)
                for index, (content, embedding) in enumerate(zip(chunks, embeddings, strict=True))
            ],
        )
        return DocumentRead.model_validate(self.repository.create(document))

    def read_document_list(self, page: int, page_size: int) -> list[DocumentRead]:
        documents = self.repository.list_(page, page_size)
        return [DocumentRead.model_validate(document) for document in documents]

    def search(self, query: str, k: int | None = None) -> PassageSearch:
        """Find the passages of the coaching corpus most relevant to a question."""
        if not self.repository.has_chunks():
            return PassageSearch(status=SearchStatus.EMPTY_CORPUS, results=[])

        query_embedding = get_embeddings([query])[0]
        if len(query_embedding) != EMBEDDING_DIMENSIONS:
            raise EmbeddingDimensionError(EMBEDDING_DIMENSIONS, len(query_embedding))

        limit = normalize_k(k)
        passages = self._to_passages(
            self.repository.search(
                query_embedding, limit * DUPLICATE_OVERFETCH, MAX_COSINE_DISTANCE
            ),
            limit,
        )
        if passages:
            return PassageSearch(status=SearchStatus.OK, results=passages)
        return PassageSearch(status=SearchStatus.NO_MATCH, results=[])

    @staticmethod
    def _to_passages(chunks: list[tuple[Chunk, float]], limit: int) -> list[PassageRead]:
        """Map retrieved chunks to passages, dropping repeated content from re-ingested docs.

        Duplicates are removed after retrieval, so the caller over-fetches: without that, a
        duplicated chunk could shrink the result below the requested count or, at k=1, turn a
        real match into a false no-match.
        """
        seen: set[str] = set()
        passages: list[PassageRead] = []
        for chunk, _distance in chunks:
            if chunk.content in seen:
                continue
            seen.add(chunk.content)
            passages.append(
                PassageRead(
                    document_id=chunk.document_id,
                    document=chunk.document.title,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                )
            )
            if len(passages) == limit:
                break
        return passages
