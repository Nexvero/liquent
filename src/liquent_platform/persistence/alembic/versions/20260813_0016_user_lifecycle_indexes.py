"""Index user lifecycle drain and historical reference lookups.

Revision ID: 20260813_0016
Revises: 20260813_0015
"""

from typing import Sequence

from alembic import op

revision: str = "20260813_0016"
down_revision: str | Sequence[str] | None = "20260813_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_browser_sessions_user", "browser_sessions", ["user_id"])
    op.create_index(
        "ix_identity_admissions_target_user",
        "identity_admissions",
        ["target_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_admissions_target_user", table_name="identity_admissions"
    )
    op.drop_index("ix_browser_sessions_user", table_name="browser_sessions")
