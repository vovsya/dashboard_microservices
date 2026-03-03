"""add site_monitors

Revision ID: c27f46cece56
Revises: 7a1fc8705775
Create Date: 2026-03-03 13:09:10.067834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c27f46cece56'
down_revision: Union[str, Sequence[str], None] = '7a1fc8705775'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE site_monitors (
      id                  BIGSERIAL PRIMARY KEY,
      user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      monitor_id          UUID,
      url                 TEXT NOT NULL,
      interval_minutes    INT NOT NULL,
      registration_status TEXT NOT NULL DEFAULT 'pending',
      last_status         TEXT,
      last_checked_at     TIMESTAMPTZ,
      last_changed        BOOLEAN,
      last_error          TEXT,
      updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      CONSTRAINT uq_site_monitors_user_url UNIQUE (user_id, url)
    );
    """)

    op.execute("""CREATE INDEX ix_site_monitors_user_id ON site_monitors (user_id);""")

    op.execute("""
    CREATE UNIQUE INDEX uq_site_monitors_monitor_id_not_null
      ON site_monitors (monitor_id)
      WHERE monitor_id IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""DROP INDEX IF EXISTS uq_site_monitors_monitor_id_not_null;""")
    op.execute("""DROP INDEX IF EXISTS ix_site_monitors_user_id;""")
    op.execute("""DROP TABLE IF EXISTS site_monitors;""")
