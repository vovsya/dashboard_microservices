"""db_creation

Revision ID: a90b46796e57
Revises: 
Create Date: 2026-01-07 12:16:26.056507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a90b46796e57'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE users (
            id          SERIAL PRIMARY KEY,
            username    TEXT NOT NULL UNIQUE,
            secretpass  TEXT NOT NULL
        )
        """
    )

    op.execute(
        """
        CREATE TABLE pages (
            user_id         INTEGER NOT NULL REFERENCES users(id),
            page            INTEGER NOT NULL,
            nickname        BOOLEAN NOT NULL DEFAULT FALSE,
            weather         BOOLEAN NOT NULL DEFAULT FALSE,
            time            BOOLEAN NOT NULL DEFAULT FALSE,
            date            BOOLEAN NOT NULL DEFAULT FALSE,
            traffic         BOOLEAN NOT NULL DEFAULT FALSE,
            currencies      BOOLEAN NOT NULL DEFAULT FALSE,
            UNIQUE (user_id, page)
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS pages
        """
    )

    op.execute(
        """
        DROP TABLE IF EXISTS users
        """
    )
