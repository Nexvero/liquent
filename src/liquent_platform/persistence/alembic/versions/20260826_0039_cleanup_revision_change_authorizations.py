"""Bind cleanup revision changes to mutation authority facts.

Revision ID: 20260826_0039
Revises: 20260826_0038
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0039"
down_revision: str | Sequence[str] | None = "20260826_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _authorization_table(kind: str, change_table: str, prefix: str) -> None:
    authority = f"mh_supervisor_cleanup_{kind}_authority"
    op.create_table(
        f"mh_supervisor_cleanup_{kind}_change_authorizations",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("authority_set_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("authorized_by_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name=f"pk_{prefix}_authorization"),
        sa.ForeignKeyConstraint(
            ["change_id"], [f"{change_table}.change_id"],
            name=f"fk_{prefix}_authorization_change",
        ),
        sa.ForeignKeyConstraint(
            ["authority_set_revision_id", "scope_id", "authorized_by_user_id"],
            [
                f"{authority}_members.revision_id",
                f"{authority}_members.scope_id",
                f"{authority}_members.user_id",
            ],
            name=f"fk_{prefix}_authorization_member",
        ),
    )


def upgrade() -> None:
    _authorization_table(
        "management",
        "manifest_handoff_supervisor_cleanup_management_changes",
        "mhscmca",
    )
    _authorization_table(
        "hold", "manifest_handoff_supervisor_cleanup_hold_changes", "mhschca"
    )
    _authorization_table(
        "recovery", "manifest_handoff_supervisor_cleanup_recovery_changes", "mhscrca"
    )
    _authorization_table(
        "reference", "manifest_handoff_supervisor_cleanup_reference_changes", "mhscfca"
    )


def downgrade() -> None:
    op.drop_table("mh_supervisor_cleanup_reference_change_authorizations")
    op.drop_table("mh_supervisor_cleanup_recovery_change_authorizations")
    op.drop_table("mh_supervisor_cleanup_hold_change_authorizations")
    op.drop_table("mh_supervisor_cleanup_management_change_authorizations")
