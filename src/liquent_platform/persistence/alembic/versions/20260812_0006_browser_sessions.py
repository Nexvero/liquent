"""Add persistent browser sessions.

Revision ID: 20260812_0006
Revises: 20260812_0005
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0006"
down_revision: str | Sequence[str] | None = "20260812_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "browser_sessions",
        sa.Column("session_id", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("csrf_token", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("session_id", name="pk_browser_sessions"),
        sa.CheckConstraint(
            "length(session_id) > 0", name="ck_browser_session_id_present"
        ),
        sa.CheckConstraint(
            "length(user_id) > 0", name="ck_browser_session_user_present"
        ),
        sa.CheckConstraint(
            "length(csrf_token) > 0", name="ck_browser_session_csrf_present"
        ),
    )


def downgrade() -> None:
    op.drop_table("browser_sessions")
