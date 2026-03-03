"""add site_monitoring to pages

Revision ID: e8c67852584a
Revises: c27f46cece56
Create Date: 2026-03-03 13:26:09.742831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8c67852584a'
down_revision: Union[str, Sequence[str], None] = 'c27f46cece56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE pages
      ADD COLUMN IF NOT EXISTS site_monitoring BOOLEAN NOT NULL DEFAULT FALSE;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE pages
      DROP COLUMN IF EXISTS site_monitoring;
    """)
