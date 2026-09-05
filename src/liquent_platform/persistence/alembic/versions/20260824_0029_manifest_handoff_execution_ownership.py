"""Add persistent manifest-handoff execution ownership and recovery facts.

Revision ID: 20260824_0029
Revises: 20260819_0028
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260824_0029"
down_revision: str | Sequence[str] | None = "20260819_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_check(column: str, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(f"length({column})>0", name=name)


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_recovery_authorities",
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "scope_id", "user_id", name="pk_manifest_handoff_recovery_authorities"
        ),
        sa.ForeignKeyConstraint(
            ["scope_id"], ["manifest_handoff_registry_scopes.scope_id"],
            name="fk_manifest_handoff_recovery_authority_scope",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"],
            name="fk_manifest_handoff_recovery_authority_user",
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive')",
            name="ck_manifest_handoff_recovery_authority_status",
        ),
    )
    op.create_table(
        "manifest_handoff_execution_claims",
        sa.Column("claim_id", sa.LargeBinary(), nullable=False),
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("owner_id", sa.LargeBinary(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("claim_id", name="pk_manifest_handoff_execution_claims"),
        sa.UniqueConstraint("attempt_id", name="uq_manifest_handoff_execution_attempt"),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["manifest_handoff_attempts.attempt_id"],
            name="fk_manifest_handoff_execution_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_manifest_handoff_execution_actor",
        ),
        _id_check("claim_id", "ck_manifest_handoff_execution_claim_present"),
        _id_check("owner_id", "ck_manifest_handoff_execution_owner_present"),
        sa.CheckConstraint(
            "lease_expires_at>claimed_at", name="ck_manifest_handoff_execution_lease"
        ),
    )
    op.create_table(
        "manifest_handoff_execution_lease_renewals",
        sa.Column("renewal_id", sa.LargeBinary(), nullable=False),
        sa.Column("claim_id", sa.LargeBinary(), nullable=False),
        sa.Column("owner_id", sa.LargeBinary(), nullable=False),
        sa.Column("renewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "renewal_id", name="pk_manifest_handoff_execution_lease_renewals"
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["manifest_handoff_execution_claims.claim_id"],
            name="fk_manifest_handoff_execution_renewal_claim",
        ),
        _id_check("renewal_id", "ck_manifest_handoff_execution_renewal_present"),
        _id_check("owner_id", "ck_manifest_handoff_execution_renewal_owner_present"),
        sa.CheckConstraint(
            "lease_expires_at>renewed_at",
            name="ck_manifest_handoff_execution_renewal_lease",
        ),
    )
    op.create_table(
        "manifest_handoff_execution_starts",
        sa.Column("claim_id", sa.LargeBinary(), nullable=False),
        sa.Column("observation_id", sa.LargeBinary(), nullable=False),
        sa.Column("owner_id", sa.LargeBinary(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("claim_id", name="pk_manifest_handoff_execution_starts"),
        sa.UniqueConstraint(
            "observation_id", name="uq_manifest_handoff_execution_start_observation"
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["manifest_handoff_execution_claims.claim_id"],
            name="fk_manifest_handoff_execution_start_claim",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["manifest_handoff_attempt_observations.observation_id"],
            name="fk_manifest_handoff_execution_start_observation",
        ),
        _id_check("owner_id", "ck_manifest_handoff_execution_start_owner_present"),
    )
    op.create_table(
        "manifest_handoff_execution_ends",
        sa.Column("end_id", sa.LargeBinary(), nullable=False),
        sa.Column("claim_id", sa.LargeBinary(), nullable=False),
        sa.Column("owner_id", sa.LargeBinary(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("end_id", name="pk_manifest_handoff_execution_ends"),
        sa.UniqueConstraint("claim_id", name="uq_manifest_handoff_execution_end_claim"),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["manifest_handoff_execution_claims.claim_id"],
            name="fk_manifest_handoff_execution_end_claim",
        ),
        _id_check("end_id", "ck_manifest_handoff_execution_end_present"),
        _id_check("owner_id", "ck_manifest_handoff_execution_end_owner_present"),
        sa.CheckConstraint(
            "kind IN ('outcome_secured','outcome_unknown','start_not_confirmed')",
            name="ck_manifest_handoff_execution_end_kind",
        ),
    )
    op.create_table(
        "manifest_handoff_recovery_claims",
        sa.Column("claim_id", sa.LargeBinary(), nullable=False),
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("execution_end_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("owner_id", sa.LargeBinary(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("claim_id", name="pk_manifest_handoff_recovery_claims"),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["manifest_handoff_attempts.attempt_id"],
            name="fk_manifest_handoff_recovery_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["execution_end_id"], ["manifest_handoff_execution_ends.end_id"],
            name="fk_manifest_handoff_recovery_execution_end",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_manifest_handoff_recovery_actor",
        ),
        _id_check("claim_id", "ck_manifest_handoff_recovery_claim_present"),
        _id_check("owner_id", "ck_manifest_handoff_recovery_owner_present"),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at>=claimed_at",
            name="ck_manifest_handoff_recovery_end_order",
        ),
    )
    op.create_index(
        "uq_manifest_handoff_active_recovery_attempt",
        "manifest_handoff_recovery_claims",
        ["attempt_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
        sqlite_where=sa.text("ended_at IS NULL"),
    )
    op.create_table(
        "manifest_handoff_recovery_ends",
        sa.Column("end_id", sa.LargeBinary(), nullable=False),
        sa.Column("claim_id", sa.LargeBinary(), nullable=False),
        sa.Column("owner_id", sa.LargeBinary(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("end_id", name="pk_manifest_handoff_recovery_ends"),
        sa.UniqueConstraint("claim_id", name="uq_manifest_handoff_recovery_end_claim"),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["manifest_handoff_recovery_claims.claim_id"],
            name="fk_manifest_handoff_recovery_end_claim",
        ),
        _id_check("end_id", "ck_manifest_handoff_recovery_end_present"),
        _id_check("owner_id", "ck_manifest_handoff_recovery_end_owner_present"),
        sa.CheckConstraint(
            "kind IN ('outcome_secured','outcome_unknown','start_not_confirmed')",
            name="ck_manifest_handoff_recovery_end_kind",
        ),
    )
    op.create_table(
        "manifest_handoff_recovery_observations",
        sa.Column("claim_id", sa.LargeBinary(), nullable=False),
        sa.Column("observation_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "claim_id", name="pk_manifest_handoff_recovery_observations"
        ),
        sa.UniqueConstraint(
            "observation_id", name="uq_manifest_handoff_recovery_observation"
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["manifest_handoff_recovery_claims.claim_id"],
            name="fk_manifest_handoff_recovery_observation_claim",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["manifest_handoff_attempt_observations.observation_id"],
            name="fk_manifest_handoff_recovery_observation_fact",
        ),
    )


def downgrade() -> None:
    op.drop_table("manifest_handoff_recovery_observations")
    op.drop_table("manifest_handoff_recovery_ends")
    op.drop_index(
        "uq_manifest_handoff_active_recovery_attempt",
        table_name="manifest_handoff_recovery_claims",
    )
    op.drop_table("manifest_handoff_recovery_claims")
    op.drop_table("manifest_handoff_execution_ends")
    op.drop_table("manifest_handoff_execution_starts")
    op.drop_table("manifest_handoff_execution_lease_renewals")
    op.drop_table("manifest_handoff_execution_claims")
    op.drop_table("manifest_handoff_recovery_authorities")
