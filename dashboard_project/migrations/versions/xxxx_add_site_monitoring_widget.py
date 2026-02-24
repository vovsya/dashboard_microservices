"""add site monitoring widget tables

Revision ID: xxxx_add_site_monitoring_widget
Revises: <PUT_YOUR_LAST_REVISION_HERE>
Create Date: 2026-02-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "xxxx_add_site_monitoring_widget"
down_revision: Union[str, Sequence[str], None] = "<PUT_YOUR_LAST_REVISION_HERE>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pages",
        sa.Column("site_monitoring", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )

    op.create_table(
        "site_monitors",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("monitor_id", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("registration_status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("last_status", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_changed", sa.Boolean(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "url", name="uq_site_monitors_user_url"),
    )
    op.create_index("ix_site_monitors_user_id", "site_monitors", ["user_id"], unique=False)
    op.create_index("ix_site_monitors_monitor_id", "site_monitors", ["monitor_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_site_monitors_monitor_id", table_name="site_monitors")
    op.drop_index("ix_site_monitors_user_id", table_name="site_monitors")
    op.drop_table("site_monitors")
    op.drop_column("pages", "site_monitoring")
