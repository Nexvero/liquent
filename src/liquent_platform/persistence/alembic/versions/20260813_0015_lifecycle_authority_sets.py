"""Add separate lifecycle-management authority set foundations.

Revision ID: 20260813_0015
Revises: 20260813_0014
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0015"
down_revision: str | Sequence[str] | None = "20260813_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _domain(prefix: str) -> None:
    revisions = f"{prefix}_authority_set_revisions"
    members = f"{prefix}_authority_set_members"
    current = f"{prefix}_authority_current_set"
    changes = f"{prefix}_authority_changes"
    op.create_table(
        revisions,
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name=f"pk_{revisions}"),
        sa.CheckConstraint("length(revision_id)>0", name=f"ck_{revisions}_id"),
    )
    op.create_table(
        members,
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", "user_id", name=f"pk_{members}"),
        sa.ForeignKeyConstraint(
            ["revision_id"], [f"{revisions}.revision_id"],
            name=f"fk_{members}_revision", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"], name=f"fk_{members}_user"
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive')", name=f"ck_{members}_status"
        ),
    )
    op.create_table(
        current,
        sa.Column("singleton_key", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("singleton_key", name=f"pk_{current}"),
        sa.ForeignKeyConstraint(
            ["revision_id"], [f"{revisions}.revision_id"],
            name=f"fk_{current}_revision",
        ),
        sa.CheckConstraint("singleton_key=1", name=f"ck_{current}_singleton"),
    )
    op.create_table(
        changes,
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("intent", sa.String(length=10), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=True),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name=f"pk_{changes}"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name=f"fk_{changes}_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name=f"fk_{changes}_target",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], [f"{revisions}.revision_id"],
            name=f"fk_{changes}_expected",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id"], [f"{revisions}.revision_id"],
            name=f"fk_{changes}_resulting",
        ),
        sa.CheckConstraint("length(change_id)>0", name=f"ck_{changes}_id"),
        sa.CheckConstraint(
            "intent IN ('anchor','grant','deactivate','reactivate')",
            name=f"ck_{changes}_intent",
        ),
        sa.CheckConstraint(
            "(intent='anchor' AND expected_revision_id IS NULL) OR "
            "(intent IN ('grant','deactivate','reactivate') "
            "AND expected_revision_id IS NOT NULL)",
            name=f"ck_{changes}_expected",
        ),
    )


def upgrade() -> None:
    _domain("user_lifecycle")
    _domain("workspace_lifecycle")


def downgrade() -> None:
    for prefix in ("workspace_lifecycle", "user_lifecycle"):
        op.drop_table(f"{prefix}_authority_changes")
        op.drop_table(f"{prefix}_authority_current_set")
        op.drop_table(f"{prefix}_authority_set_members")
        op.drop_table(f"{prefix}_authority_set_revisions")
