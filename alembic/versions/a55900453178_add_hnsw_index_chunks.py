"""add hnsw index chunks

Revision ID: a55900453178
Revises: bbd4c970a463
Create Date: 2026-10-22 01:55:39.276243

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a55900453178"
down_revision: str | Sequence[str] | None = "bbd4c970a463"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw"
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw")
