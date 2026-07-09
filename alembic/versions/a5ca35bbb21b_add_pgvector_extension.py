"""add_pgvector_extension

Revision ID: a5ca35bbb21b
Revises: 2fdcc079a0df
Create Date: 2026-07-09 16:20:52.522311

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5ca35bbb21b"
down_revision: Union[str, Sequence[str], None] = "2fdcc079a0df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS vector;")
