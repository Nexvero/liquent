"""Add supervisor cleanup retention policy and authority foundation.

Revision ID: 20260826_0042
Revises: 20260826_0041
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0042"
down_revision: str | Sequence[str] | None = "20260826_0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_POLICIES = "mh_supervisor_cleanup_retention_policy_revisions"
_ACTIVE = "mh_supervisor_cleanup_retention_policy_active"
_CHANGES = "mh_supervisor_cleanup_retention_policy_changes"
_SETS = "mh_supervisor_cleanup_retention_policy_authority_sets"
_MEMBERS = "mh_supervisor_cleanup_retention_policy_authority_members"
_CURRENT = "mh_supervisor_cleanup_retention_policy_authority_current"
_AUTHORITY_CHANGES = "mh_supervisor_cleanup_retention_policy_authority_changes"
_BOOTSTRAPS = "mh_supervisor_cleanup_retention_policy_bootstraps"
_RECOVERIES = "mh_supervisor_cleanup_retention_policy_authority_recoveries"


def _id(column: str, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(f"length({column})>0", name=name)


def _data_class(name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "data_class='supervisor_control_directory'", name=name
    )


def upgrade() -> None:
    op.create_table(
        _POLICIES,
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("minimum_retention_seconds", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", name="pk_mh_supervisor_cleanup_retention_policies"
        ),
        sa.UniqueConstraint(
            "revision_id", "data_class",
            name="uq_mh_supervisor_cleanup_retention_policy_binding",
        ),
        _id("revision_id", "ck_mh_supervisor_cleanup_retention_policy_id"),
        _data_class("ck_mh_supervisor_cleanup_retention_policy_data_class"),
        sa.CheckConstraint(
            "minimum_retention_seconds>0",
            name="ck_mh_supervisor_cleanup_retention_policy_duration",
        ),
    )
    op.create_table(
        _SETS,
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", name="pk_mh_supervisor_cleanup_retention_authority_sets"
        ),
        sa.UniqueConstraint(
            "revision_id", "data_class",
            name="uq_mh_supervisor_cleanup_retention_authority_set_binding",
        ),
        sa.UniqueConstraint(
            "data_class", "sequence_number",
            name="uq_mh_supervisor_cleanup_retention_authority_sequence",
        ),
        _id("revision_id", "ck_mh_supervisor_cleanup_retention_authority_set_id"),
        _data_class("ck_mh_supervisor_cleanup_retention_authority_data_class"),
        sa.CheckConstraint(
            "sequence_number>0",
            name="ck_mh_supervisor_cleanup_retention_authority_sequence",
        ),
    )
    op.create_table(
        _MEMBERS,
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "user_id",
            name="pk_mh_supervisor_cleanup_retention_authority_members",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "data_class"],
            [f"{_SETS}.revision_id", f"{_SETS}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_authority_member_set",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"],
            name="fk_mh_supervisor_cleanup_retention_authority_member_user",
        ),
        _data_class("ck_mh_supervisor_cleanup_retention_authority_member_class"),
        sa.CheckConstraint(
            "status IN ('active','inactive')",
            name="ck_mh_supervisor_cleanup_retention_authority_member_status",
        ),
    )
    op.create_table(
        _ACTIVE,
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "data_class", name="pk_mh_supervisor_cleanup_retention_policy_active"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "data_class"],
            [f"{_POLICIES}.revision_id", f"{_POLICIES}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_policy_active_revision",
        ),
        _data_class("ck_mh_supervisor_cleanup_retention_policy_active_class"),
    )
    op.create_table(
        _CURRENT,
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "data_class", name="pk_mh_supervisor_cleanup_retention_authority_current"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "data_class"],
            [f"{_SETS}.revision_id", f"{_SETS}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_authority_current_set",
        ),
        _data_class("ck_mh_supervisor_cleanup_retention_authority_current_class"),
    )
    op.create_table(
        _CHANGES,
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=True),
        sa.Column("result_revision_id", sa.LargeBinary(), nullable=True),
        sa.Column("intent", sa.String(length=10), nullable=False),
        sa.Column("minimum_retention_seconds", sa.BigInteger(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "change_id", name="pk_mh_supervisor_cleanup_retention_policy_changes"
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_mh_supervisor_cleanup_retention_policy_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], [f"{_POLICIES}.revision_id"],
            name="fk_mh_supervisor_cleanup_retention_policy_change_expected",
        ),
        sa.ForeignKeyConstraint(
            ["result_revision_id", "data_class"],
            [f"{_POLICIES}.revision_id", f"{_POLICIES}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_policy_change_result",
        ),
        _id("change_id", "ck_mh_supervisor_cleanup_retention_policy_change_id"),
        _data_class("ck_mh_supervisor_cleanup_retention_policy_change_class"),
        sa.CheckConstraint(
            "(intent='replace' AND result_revision_id IS NOT NULL "
            "AND minimum_retention_seconds>0) OR "
            "(intent='deactivate' AND expected_revision_id IS NOT NULL "
            "AND result_revision_id IS NULL AND minimum_retention_seconds IS NULL)",
            name="ck_mh_supervisor_cleanup_retention_policy_change_values",
        ),
    )
    op.create_table(
        _AUTHORITY_CHANGES,
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("result_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("intent", sa.String(length=10), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "change_id", name="pk_mh_supervisor_cleanup_retention_authority_changes"
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_mh_supervisor_cleanup_retention_authority_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_mh_supervisor_cleanup_retention_authority_change_target",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id", "data_class"],
            [f"{_SETS}.revision_id", f"{_SETS}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_authority_change_expected",
        ),
        sa.ForeignKeyConstraint(
            ["result_revision_id", "data_class"],
            [f"{_SETS}.revision_id", f"{_SETS}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_authority_change_result",
        ),
        _id("change_id", "ck_mh_supervisor_cleanup_retention_authority_change_id"),
        _data_class("ck_mh_supervisor_cleanup_retention_authority_change_class"),
        sa.CheckConstraint(
            "intent IN ('grant','deactivate','reactivate')",
            name="ck_mh_supervisor_cleanup_retention_authority_change_intent",
        ),
    )
    op.create_table(
        _BOOTSTRAPS,
        sa.Column("bootstrap_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("policy_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("authority_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("minimum_retention_seconds", sa.BigInteger(), nullable=False),
        sa.Column("bootstrapped_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "bootstrap_id", name="pk_mh_supervisor_cleanup_retention_bootstraps"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_mh_supervisor_cleanup_retention_bootstrap_target",
        ),
        sa.ForeignKeyConstraint(
            ["policy_revision_id", "data_class"],
            [f"{_POLICIES}.revision_id", f"{_POLICIES}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_bootstrap_policy",
        ),
        sa.ForeignKeyConstraint(
            ["authority_revision_id", "data_class"],
            [f"{_SETS}.revision_id", f"{_SETS}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_bootstrap_authority",
        ),
        _id("bootstrap_id", "ck_mh_supervisor_cleanup_retention_bootstrap_id"),
        _data_class("ck_mh_supervisor_cleanup_retention_bootstrap_class"),
        sa.CheckConstraint(
            "minimum_retention_seconds>0",
            name="ck_mh_supervisor_cleanup_retention_bootstrap_duration",
        ),
    )
    op.create_table(
        _RECOVERIES,
        sa.Column("recovery_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("result_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "recovery_id", name="pk_mh_supervisor_cleanup_retention_authority_recoveries"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_mh_supervisor_cleanup_retention_authority_recovery_target",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id", "data_class"],
            [f"{_SETS}.revision_id", f"{_SETS}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_authority_recovery_expected",
        ),
        sa.ForeignKeyConstraint(
            ["result_revision_id", "data_class"],
            [f"{_SETS}.revision_id", f"{_SETS}.data_class"],
            name="fk_mh_supervisor_cleanup_retention_authority_recovery_result",
        ),
        _id("recovery_id", "ck_mh_supervisor_cleanup_retention_authority_recovery_id"),
        _data_class("ck_mh_supervisor_cleanup_retention_authority_recovery_class"),
    )


def downgrade() -> None:
    op.drop_table(_RECOVERIES)
    op.drop_table(_BOOTSTRAPS)
    op.drop_table(_AUTHORITY_CHANGES)
    op.drop_table(_CHANGES)
    op.drop_table(_CURRENT)
    op.drop_table(_ACTIVE)
    op.drop_table(_MEMBERS)
    op.drop_table(_SETS)
    op.drop_table(_POLICIES)
