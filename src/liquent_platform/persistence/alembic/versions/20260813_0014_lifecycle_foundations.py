"""Add separate user and workspace lifecycle foundations.

Revision ID: 20260813_0014
Revises: 20260812_0013
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0014"
down_revision: str | Sequence[str] | None = "20260812_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS = "status IN ('active','inactive')"


def _authority(name: str) -> None:
    op.create_table(
        name,
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name=f"pk_{name}"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"], name=f"fk_{name}_user"
        ),
        sa.CheckConstraint(_STATUS, name=f"ck_{name}_status"),
    )


def _user_lifecycle() -> None:
    op.create_table(
        "user_lifecycle_revisions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name="pk_user_lifecycle_revisions"),
        sa.CheckConstraint(
            "length(revision_id) > 0", name="ck_user_lifecycle_revision_present"
        ),
    )
    op.create_table(
        "user_lifecycle_revision_members",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "user_id", name="pk_user_lifecycle_revision_members"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["user_lifecycle_revisions.revision_id"],
            name="fk_user_lifecycle_member_revision", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"],
            name="fk_user_lifecycle_member_user",
        ),
        sa.CheckConstraint(_STATUS, name="ck_user_lifecycle_member_status"),
    )
    op.create_table(
        "user_lifecycle_current_revision",
        sa.Column("singleton_key", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "singleton_key", name="pk_user_lifecycle_current_revision"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["user_lifecycle_revisions.revision_id"],
            name="fk_user_lifecycle_current_revision",
        ),
        sa.CheckConstraint(
            "singleton_key = 1", name="ck_user_lifecycle_current_singleton"
        ),
    )
    op.create_table(
        "user_lifecycle_changes",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("intent", sa.String(length=10), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name="pk_user_lifecycle_changes"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_user_lifecycle_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_user_lifecycle_change_target",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], ["user_lifecycle_revisions.revision_id"],
            name="fk_user_lifecycle_change_expected",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id"], ["user_lifecycle_revisions.revision_id"],
            name="fk_user_lifecycle_change_resulting",
        ),
        sa.CheckConstraint(
            "length(change_id) > 0", name="ck_user_lifecycle_change_present"
        ),
        sa.CheckConstraint(
            "intent IN ('create','deactivate','reactivate')",
            name="ck_user_lifecycle_change_intent",
        ),
    )


def _workspace_lifecycle() -> None:
    op.create_table(
        "workspace_lifecycle_revisions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", name="pk_workspace_lifecycle_revisions"
        ),
        sa.CheckConstraint(
            "length(revision_id) > 0", name="ck_workspace_lifecycle_revision_present"
        ),
    )
    op.create_table(
        "workspace_lifecycle_revision_members",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "workspace_id",
            name="pk_workspace_lifecycle_revision_members",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["workspace_lifecycle_revisions.revision_id"],
            name="fk_workspace_lifecycle_member_revision", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_workspace_lifecycle_member_workspace",
        ),
        sa.CheckConstraint(_STATUS, name="ck_workspace_lifecycle_member_status"),
    )
    op.create_table(
        "workspace_lifecycle_current_revision",
        sa.Column("singleton_key", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "singleton_key", name="pk_workspace_lifecycle_current_revision"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["workspace_lifecycle_revisions.revision_id"],
            name="fk_workspace_lifecycle_current_revision",
        ),
        sa.CheckConstraint(
            "singleton_key = 1", name="ck_workspace_lifecycle_current_singleton"
        ),
    )
    op.create_table(
        "workspace_lifecycle_changes",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column(
            "initial_onboarding_manager_user_id", sa.LargeBinary(), nullable=True
        ),
        sa.Column("intent", sa.String(length=10), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name="pk_workspace_lifecycle_changes"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_workspace_lifecycle_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_workspace_lifecycle_change_target",
        ),
        sa.ForeignKeyConstraint(
            ["initial_onboarding_manager_user_id"], ["identity_users.user_id"],
            name="fk_workspace_lifecycle_change_manager",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], ["workspace_lifecycle_revisions.revision_id"],
            name="fk_workspace_lifecycle_change_expected",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id"], ["workspace_lifecycle_revisions.revision_id"],
            name="fk_workspace_lifecycle_change_resulting",
        ),
        sa.CheckConstraint(
            "length(change_id) > 0", name="ck_workspace_lifecycle_change_present"
        ),
        sa.CheckConstraint(
            "intent IN ('create','deactivate')",
            name="ck_workspace_lifecycle_change_intent",
        ),
        sa.CheckConstraint(
            "(intent='create' AND initial_onboarding_manager_user_id IS NOT NULL) "
            "OR (intent='deactivate' AND initial_onboarding_manager_user_id IS NULL)",
            name="ck_workspace_lifecycle_change_manager",
        ),
    )


def upgrade() -> None:
    _authority("user_lifecycle_management_authorities")
    _authority("workspace_lifecycle_management_authorities")
    _user_lifecycle()
    _workspace_lifecycle()


def downgrade() -> None:
    op.drop_table("workspace_lifecycle_changes")
    op.drop_table("workspace_lifecycle_current_revision")
    op.drop_table("workspace_lifecycle_revision_members")
    op.drop_table("workspace_lifecycle_revisions")
    op.drop_table("user_lifecycle_changes")
    op.drop_table("user_lifecycle_current_revision")
    op.drop_table("user_lifecycle_revision_members")
    op.drop_table("user_lifecycle_revisions")
    op.drop_table("workspace_lifecycle_management_authorities")
    op.drop_table("user_lifecycle_management_authorities")
