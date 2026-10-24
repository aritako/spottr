from sqlalchemy import select
from sqlalchemy.orm.session import Session

from app.core.models import Document


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
