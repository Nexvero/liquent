"""Add separate OIDC and membership authority lifecycle foundations.

Revision ID: 20260812_0013
Revises: 20260812_0012
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0013"
down_revision: str | Sequence[str] | None = "20260812_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS = "status IN ('active','inactive')"
_INTENT = "intent IN ('anchor','grant','deactivate','reactivate')"
_EXPECTED_REVISION = (
    "(intent = 'anchor' AND expected_revision_id IS NULL) OR "
    "(intent IN ('grant','deactivate','reactivate') "
    "AND expected_revision_id IS NOT NULL)"
)


def upgrade() -> None:
    op.create_table(
        "oidc_trust_authority_set_revisions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name="pk_oidc_authority_set_revisions"),
        sa.CheckConstraint(
            "length(revision_id) > 0", name="ck_oidc_authority_set_revision_present"
        ),
    )
    op.create_table(
        "oidc_trust_authority_set_members",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "user_id", name="pk_oidc_authority_set_members"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["oidc_trust_authority_set_revisions.revision_id"],
            name="fk_oidc_authority_set_member_revision", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"],
            name="fk_oidc_authority_set_member_user",
        ),
        sa.CheckConstraint(_STATUS, name="ck_oidc_authority_set_member_status"),
    )
    op.create_table(
        "oidc_trust_authority_current_set",
        sa.Column("singleton_key", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("singleton_key", name="pk_oidc_authority_current_set"),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["oidc_trust_authority_set_revisions.revision_id"],
            name="fk_oidc_authority_current_revision",
        ),
        sa.CheckConstraint("singleton_key = 1", name="ck_oidc_authority_current_singleton"),
    )
    op.create_table(
        "oidc_trust_authority_lifecycle_changes",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("intent", sa.String(length=10), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=True),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name="pk_oidc_authority_changes"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_oidc_authority_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_oidc_authority_change_target",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], ["oidc_trust_authority_set_revisions.revision_id"],
            name="fk_oidc_authority_change_expected",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id"], ["oidc_trust_authority_set_revisions.revision_id"],
            name="fk_oidc_authority_change_resulting",
        ),
        sa.CheckConstraint("length(change_id) > 0", name="ck_oidc_authority_change_present"),
        sa.CheckConstraint(_INTENT, name="ck_oidc_authority_change_intent"),
        sa.CheckConstraint(
            _EXPECTED_REVISION, name="ck_oidc_authority_change_expected"
        ),
    )
    op.create_table(
        "oidc_trust_authority_recoveries",
        sa.Column("recovery_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("recovery_id", name="pk_oidc_authority_recoveries"),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_oidc_authority_recovery_target",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], ["oidc_trust_authority_set_revisions.revision_id"],
            name="fk_oidc_authority_recovery_expected",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id"], ["oidc_trust_authority_set_revisions.revision_id"],
            name="fk_oidc_authority_recovery_resulting",
        ),
        sa.CheckConstraint("length(recovery_id) > 0", name="ck_oidc_authority_recovery_present"),
    )

    op.create_table(
        "workspace_membership_authority_set_revisions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name="pk_membership_authority_set_revisions"),
        sa.UniqueConstraint(
            "revision_id", "workspace_id", name="uq_membership_authority_revision_scope"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_membership_authority_set_workspace",
        ),
        sa.CheckConstraint(
            "length(revision_id) > 0", name="ck_membership_authority_set_revision_present"
        ),
    )
    op.create_table(
        "workspace_membership_authority_set_members",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "user_id", name="pk_membership_authority_set_members"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["workspace_membership_authority_set_revisions.revision_id"],
            name="fk_membership_authority_set_member_revision", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"],
            name="fk_membership_authority_set_member_user",
        ),
        sa.CheckConstraint(_STATUS, name="ck_membership_authority_set_member_status"),
    )
    op.create_table(
        "workspace_membership_authority_current_sets",
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", name="pk_membership_authority_current_sets"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_membership_authority_current_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "workspace_id"],
            [
                "workspace_membership_authority_set_revisions.revision_id",
                "workspace_membership_authority_set_revisions.workspace_id",
            ],
            name="fk_membership_authority_current_revision",
        ),
    )
    op.create_table(
        "workspace_membership_authority_lifecycle_changes",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("intent", sa.String(length=10), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=True),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name="pk_membership_authority_changes"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_membership_authority_change_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_membership_authority_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_membership_authority_change_target",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id", "workspace_id"],
            [
                "workspace_membership_authority_set_revisions.revision_id",
                "workspace_membership_authority_set_revisions.workspace_id",
            ],
            name="fk_membership_authority_change_expected",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id", "workspace_id"],
            [
                "workspace_membership_authority_set_revisions.revision_id",
                "workspace_membership_authority_set_revisions.workspace_id",
            ],
            name="fk_membership_authority_change_resulting",
        ),
        sa.CheckConstraint("length(change_id) > 0", name="ck_membership_authority_change_present"),
        sa.CheckConstraint(_INTENT, name="ck_membership_authority_change_intent"),
        sa.CheckConstraint(
            _EXPECTED_REVISION, name="ck_membership_authority_change_expected"
        ),
    )
    op.create_table(
        "workspace_membership_authority_recoveries",
        sa.Column("recovery_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("recovery_id", name="pk_membership_authority_recoveries"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_membership_authority_recovery_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_membership_authority_recovery_target",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id", "workspace_id"],
            [
                "workspace_membership_authority_set_revisions.revision_id",
                "workspace_membership_authority_set_revisions.workspace_id",
            ],
            name="fk_membership_authority_recovery_expected",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id", "workspace_id"],
            [
                "workspace_membership_authority_set_revisions.revision_id",
                "workspace_membership_authority_set_revisions.workspace_id",
            ],
            name="fk_membership_authority_recovery_resulting",
        ),
        sa.CheckConstraint(
            "length(recovery_id) > 0", name="ck_membership_authority_recovery_present"
        ),
    )


def downgrade() -> None:
    op.drop_table("workspace_membership_authority_recoveries")
    op.drop_table("workspace_membership_authority_lifecycle_changes")
    op.drop_table("workspace_membership_authority_current_sets")
    op.drop_table("workspace_membership_authority_set_members")
    op.drop_table("workspace_membership_authority_set_revisions")
    op.drop_table("oidc_trust_authority_recoveries")
    op.drop_table("oidc_trust_authority_lifecycle_changes")
    op.drop_table("oidc_trust_authority_current_set")
    op.drop_table("oidc_trust_authority_set_members")
    op.drop_table("oidc_trust_authority_set_revisions")
