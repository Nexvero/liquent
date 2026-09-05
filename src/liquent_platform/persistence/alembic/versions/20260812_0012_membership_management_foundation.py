"""Add workspace membership-management authority and revision foundation.

Revision ID: 20260812_0012
Revises: 20260812_0011
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0012"
down_revision: str | Sequence[str] | None = "20260812_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_membership_management_authorities",
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "user_id", "workspace_id", name="pk_membership_management_authority"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"],
            name="fk_membership_management_actor",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_membership_management_workspace",
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive')",
            name="ck_membership_management_authority_status",
        ),
    )
    op.create_table(
        "workspace_membership_revisions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name="pk_membership_revisions"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"],
            name="fk_membership_revision_user",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_membership_revision_workspace",
        ),
        sa.CheckConstraint(
            "length(revision_id) > 0", name="ck_membership_revision_id_present"
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive')", name="ck_membership_revision_status"
        ),
    )
    op.create_table(
        "workspace_membership_revision_permissions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("permission", sa.String(length=14), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "permission", name="pk_membership_revision_permissions"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["workspace_membership_revisions.revision_id"],
            name="fk_membership_revision_permission",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "permission IN ('research:read','research:write')",
            name="ck_membership_revision_permission",
        ),
    )
    with op.batch_alter_table("workspace_memberships") as batch:
        batch.add_column(
            sa.Column("revision_id", sa.LargeBinary(), nullable=True)
        )
        batch.create_foreign_key(
            "fk_workspace_membership_current_revision",
            "workspace_membership_revisions",
            ["revision_id"],
            ["revision_id"],
        )
    op.create_table(
        "authorized_workspace_membership_changes",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=True),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name="pk_membership_changes"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_membership_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_membership_change_target",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_membership_change_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], ["workspace_membership_revisions.revision_id"],
            name="fk_membership_change_expected_revision",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id"], ["workspace_membership_revisions.revision_id"],
            name="fk_membership_change_resulting_revision",
        ),
        sa.CheckConstraint(
            "length(change_id) > 0", name="ck_membership_change_id_present"
        ),
    )


def downgrade() -> None:
    op.drop_table("authorized_workspace_membership_changes")
    with op.batch_alter_table("workspace_memberships") as batch:
        batch.drop_constraint(
            "fk_workspace_membership_current_revision", type_="foreignkey"
        )
        batch.drop_column("revision_id")
    op.drop_table("workspace_membership_revision_permissions")
    op.drop_table("workspace_membership_revisions")
    op.drop_table("workspace_membership_management_authorities")
