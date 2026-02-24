"""add_todoes_diets_dates

Revision ID: f0074eddcb93
Revises: a90b46796e57
Create Date: 2026-01-07 14:15:05.813924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0074eddcb93'
down_revision: Union[str, Sequence[str], None] = 'a90b46796e57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE todos (
            user_id         INTEGER NOT NULL REFERENCES users(id),
            date            DATE NOT NULL,
            task            TEXT NOT NULL,
            number          INTEGER NOT NULL UNIQUE,
            UNIQUE (user_id, number)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE diets (
            user_id         INTEGER NOT NULL REFERENCES users(id),
            date            DATE NOT NULL,
            breakfast       TEXT,
            lunch           TEXT,
            dinner          TEXT,
            UNIQUE (user_id, date)
        )
        """
    )

def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS diets
        """
    )
    op.execute(
        """
        DROP TABLE IF EXISTS todos
        """
    )
