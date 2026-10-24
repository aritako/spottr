from sqlalchemy.orm import Session

from app.api.repository.docs import DocsRepository
from app.core.models import Chunk, Document
from app.engine.rag import chunk_text, get_embeddings
from app.shared.errors.docs import EmptyDocumentError
from app.shared.schemas.docs import DocumentRead


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
