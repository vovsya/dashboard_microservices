"""pages_update

Revision ID: 7a1fc8705775
Revises: f0074eddcb93
Create Date: 2026-01-09 19:13:53.237134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1fc8705775'
down_revision: Union[str, Sequence[str], None] = 'f0074eddcb93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE pages
            ADD COLUMN todo BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN diet BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE pages
            DROP COLUMN todo,
            DROP COLUMN diet;
        """
    )
