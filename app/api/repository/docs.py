from sqlalchemy import exists, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.session import Session

from app.core.models import Chunk, Document


class DocsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, document: Document) -> Document:
        try:
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            return document
        except Exception as e:
            self.db.rollback()
            raise e

    def list_(self, page: int, page_size: int) -> list[Document]:
        query = select(Document).offset(page * page_size).limit(page_size)
        return list(self.db.scalars(query))

    def search(
        self, query_embedding: list[float], k: int, max_distance: float
    ) -> list[tuple[Chunk, float]]:
        """Return the closest chunks to an embedding, paired with their cosine distance.

        The distance cutoff is applied in SQL so the ordered index scan stops early instead
        of fetching rows the caller would discard.
        """
        distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
        query = (
            select(Chunk, distance)
            .options(selectinload(Chunk.document))
            .where(distance < max_distance)
            .order_by(distance)
            .limit(k)
        )
        return [(row[0], float(row[1])) for row in self.db.execute(query).all()]

    def has_chunks(self) -> bool:
        return bool(self.db.scalar(select(exists().select_from(Chunk))))
