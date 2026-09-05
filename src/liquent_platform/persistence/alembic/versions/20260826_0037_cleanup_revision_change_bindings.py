"""Add cleanup revision change identity bindings.

Revision ID: 20260826_0037
Revises: 20260825_0036
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0037"
down_revision: str | Sequence[str] | None = "20260825_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _target_change_table(kind: str) -> None:
    table = f"manifest_handoff_supervisor_cleanup_{kind}_changes"
    revisions = f"manifest_handoff_supervisor_cleanup_{kind}_revisions"
    prefix = f"mh_supervisor_cleanup_{kind}_change"
    op.create_table(
        table,
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("directory_id", sa.LargeBinary(), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint("change_id", name=f"pk_{prefix}"),
        sa.UniqueConstraint("revision_id", name=f"uq_{prefix}_revision"),
        sa.ForeignKeyConstraint(
            ["revision_id", "directory_id"],
            [f"{revisions}.revision_id", f"{revisions}.directory_id"],
            name=f"fk_{prefix}_result",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id", "directory_id"],
            [f"{revisions}.revision_id", f"{revisions}.directory_id"],
            name=f"fk_{prefix}_expected",
        ),
        sa.CheckConstraint("length(change_id)>0", name=f"ck_{prefix}_id"),
        sa.CheckConstraint(
            "expected_revision_id IS NULL OR expected_revision_id<>revision_id",
            name=f"ck_{prefix}_predecessor",
        ),
    )


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_supervisor_cleanup_management_changes",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint(
            "change_id", name="pk_mh_supervisor_cleanup_management_change"
        ),
        sa.UniqueConstraint(
            "revision_id", name="uq_mh_supervisor_cleanup_management_change_revision"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "actor_user_id", "scope_id"],
            [
                "manifest_handoff_supervisor_cleanup_management_revisions.revision_id",
                "manifest_handoff_supervisor_cleanup_management_revisions.actor_user_id",
                "manifest_handoff_supervisor_cleanup_management_revisions.scope_id",
            ],
            name="fk_mh_supervisor_cleanup_management_change_result",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id", "actor_user_id", "scope_id"],
            [
                "manifest_handoff_supervisor_cleanup_management_revisions.revision_id",
                "manifest_handoff_supervisor_cleanup_management_revisions.actor_user_id",
                "manifest_handoff_supervisor_cleanup_management_revisions.scope_id",
            ],
            name="fk_mh_supervisor_cleanup_management_change_expected",
        ),
        sa.CheckConstraint(
            "length(change_id)>0",
            name="ck_mh_supervisor_cleanup_management_change_id",
        ),
        sa.CheckConstraint(
            "expected_revision_id IS NULL OR expected_revision_id<>revision_id",
            name="ck_mh_supervisor_cleanup_management_change_predecessor",
        ),
    )
    _target_change_table("hold")
    _target_change_table("recovery")
    _target_change_table("reference")


def downgrade() -> None:
    op.drop_table("manifest_handoff_supervisor_cleanup_reference_changes")
    op.drop_table("manifest_handoff_supervisor_cleanup_recovery_changes")
    op.drop_table("manifest_handoff_supervisor_cleanup_hold_changes")
    op.drop_table("manifest_handoff_supervisor_cleanup_management_changes")
