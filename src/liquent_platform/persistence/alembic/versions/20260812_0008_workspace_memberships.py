"""Add persistent workspace memberships and research permissions.

Revision ID: 20260812_0008
Revises: 20260812_0007
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0008"
down_revision: str | Sequence[str] | None = "20260812_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_memberships",
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "user_id", "workspace_id", name="pk_workspace_memberships"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"], name="fk_membership_user"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["identity_workspaces.workspace_id"],
            name="fk_membership_workspace",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_membership_status"
        ),
    )
    op.create_table(
        "workspace_membership_permissions",
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("permission", sa.String(length=14), nullable=False),
        sa.PrimaryKeyConstraint(
            "user_id",
            "workspace_id",
            "permission",
            name="pk_workspace_membership_permissions",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "workspace_id"],
            ["workspace_memberships.user_id", "workspace_memberships.workspace_id"],
            name="fk_permission_membership",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "permission IN ('research:read', 'research:write')",
            name="ck_membership_permission",
        ),
    )


def downgrade() -> None:
    op.drop_table("workspace_membership_permissions")
    op.drop_table("workspace_memberships")
