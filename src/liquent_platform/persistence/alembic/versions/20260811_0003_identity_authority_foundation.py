"""Add persistent internal users, workspaces, and onboarding authority.

Revision ID: 20260811_0003
Revises: 20260811_0002

Identifiers remain raw bytes so equality and uniqueness are independent of
text collation. The revision seeds nothing and fails rather than inventing a
missing user or workspace for an existing identity reference.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260811_0003"
down_revision: str | Sequence[str] | None = "20260811_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "internal_users",
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name="pk_internal_users"),
        sa.CheckConstraint("length(user_id) > 0", name="ck_internal_users_id_present"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_internal_users_status"
        ),
    )
    op.create_table(
        "workspaces",
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", name="pk_workspaces"),
        sa.CheckConstraint(
            "length(workspace_id) > 0", name="ck_workspaces_id_present"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_workspaces_status"
        ),
    )
    op.create_table(
        "workspace_onboarding_authorities",
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint(
            "user_id", "workspace_id", name="pk_workspace_onboarding_authorities"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["internal_users.user_id"],
            name="fk_workspace_onboarding_authorities_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.workspace_id"],
            name="fk_workspace_onboarding_authorities_workspace",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "length(user_id) > 0",
            name="ck_workspace_onboarding_authorities_user_present",
        ),
        sa.CheckConstraint(
            "length(workspace_id) > 0",
            name="ck_workspace_onboarding_authorities_workspace_present",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_workspace_onboarding_authorities_status",
        ),
    )

    with op.batch_alter_table("external_identity_bindings") as batch:
        batch.create_foreign_key(
            "fk_external_identity_bindings_user",
            "internal_users",
            ["user_id"],
            ["user_id"],
            ondelete="RESTRICT",
        )
    with op.batch_alter_table("identity_admissions") as batch:
        batch.create_foreign_key(
            "fk_identity_admissions_target_user",
            "internal_users",
            ["target_user_id"],
            ["user_id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_identity_admissions_target_workspace",
            "workspaces",
            ["target_workspace_id"],
            ["workspace_id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("identity_admissions") as batch:
        batch.drop_constraint(
            "fk_identity_admissions_target_workspace", type_="foreignkey"
        )
        batch.drop_constraint(
            "fk_identity_admissions_target_user", type_="foreignkey"
        )
    with op.batch_alter_table("external_identity_bindings") as batch:
        batch.drop_constraint("fk_external_identity_bindings_user", type_="foreignkey")

    op.drop_table("workspace_onboarding_authorities")
    op.drop_table("workspaces")
    op.drop_table("internal_users")
