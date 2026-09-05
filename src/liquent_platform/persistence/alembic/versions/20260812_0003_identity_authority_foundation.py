"""Add persistent users, workspaces, and onboarding-management authority.

Revision ID: 20260812_0003
Revises: 20260811_0002
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0003"
down_revision: str | Sequence[str] | None = "20260811_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_OR_INACTIVE = "status IN ('active', 'inactive')"


def upgrade() -> None:
    op.create_table(
        "identity_users",
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name="pk_identity_users"),
        sa.CheckConstraint("length(user_id) > 0", name="ck_identity_users_id_present"),
        sa.CheckConstraint(_ACTIVE_OR_INACTIVE, name="ck_identity_users_status"),
    )
    op.create_table(
        "identity_workspaces",
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", name="pk_identity_workspaces"),
        sa.CheckConstraint(
            "length(workspace_id) > 0", name="ck_identity_workspaces_id_present"
        ),
        sa.CheckConstraint(_ACTIVE_OR_INACTIVE, name="ck_identity_workspaces_status"),
    )
    op.create_table(
        "workspace_onboarding_management",
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "user_id", "workspace_id", name="pk_workspace_onboarding_management"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"], name="fk_management_user"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["identity_workspaces.workspace_id"],
            name="fk_management_workspace",
        ),
        sa.CheckConstraint(
            _ACTIVE_OR_INACTIVE, name="ck_workspace_onboarding_management_status"
        ),
    )


def downgrade() -> None:
    op.drop_table("workspace_onboarding_management")
    op.drop_table("identity_workspaces")
    op.drop_table("identity_users")
