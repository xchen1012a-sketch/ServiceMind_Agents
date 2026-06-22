"""bootstrap foundation schema

Revision ID: 20260622_001
Revises:
Create Date: 2026-06-22

Purpose: create the first ServiceMind Agents database foundation.
Recovery: this is a pre-release bootstrap migration. Downgrade drops all
tables from SQLAlchemy metadata in reverse dependency order.
"""

from collections.abc import Sequence

from alembic import op
from app import models  # noqa: F401
from app.db.base import Base

revision: str = "20260622_001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    op.execute("DROP EXTENSION IF EXISTS vector")
