"""Add persistent private manifest-handoff attempt registry foundation.

Revision ID: 20260819_0028
Revises: 20260819_0027
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260819_0028"
down_revision: str | Sequence[str] | None = "20260819_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_registry_scopes",
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("scope_id", name="pk_manifest_handoff_registry_scopes"),
        sa.CheckConstraint("length(scope_id)>0", name="ck_manifest_handoff_scope_present"),
        sa.CheckConstraint(
            "status IN ('active','inactive')", name="ck_manifest_handoff_scope_status"
        ),
    )
    op.create_table(
        "manifest_handoff_registry_authorities",
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "scope_id", "user_id", name="pk_manifest_handoff_registry_authorities"
        ),
        sa.ForeignKeyConstraint(
            ["scope_id"],
            ["manifest_handoff_registry_scopes.scope_id"],
            name="fk_manifest_handoff_registry_authority_scope",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity_users.user_id"],
            name="fk_manifest_handoff_registry_authority_user",
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive')", name="ck_manifest_handoff_authority_status"
        ),
    )
    op.create_table(
        "manifest_handoff_attempts",
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("reservation_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("handoff_name", sa.String(length=128), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("attempt_id", name="pk_manifest_handoff_attempts"),
        sa.UniqueConstraint(
            "reservation_id", name="uq_manifest_handoff_attempt_reservation"
        ),
        sa.UniqueConstraint(
            "scope_id", "handoff_name", name="uq_manifest_handoff_attempt_scope_name"
        ),
        sa.ForeignKeyConstraint(
            ["scope_id"],
            ["manifest_handoff_registry_scopes.scope_id"],
            name="fk_manifest_handoff_attempt_scope",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["identity_users.user_id"],
            name="fk_manifest_handoff_attempt_actor",
        ),
        sa.CheckConstraint(
            "length(attempt_id)>0", name="ck_manifest_handoff_attempt_present"
        ),
        sa.CheckConstraint(
            "length(reservation_id)>0", name="ck_manifest_handoff_reservation_present"
        ),
        sa.CheckConstraint(
            "length(handoff_name)>0", name="ck_manifest_handoff_name_present"
        ),
    )
    op.create_table(
        "manifest_handoff_attempt_observations",
        sa.Column("observation_id", sa.LargeBinary(), nullable=False),
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "observation_id", name="pk_manifest_handoff_attempt_observations"
        ),
        sa.UniqueConstraint(
            "attempt_id",
            "sequence_number",
            name="uq_manifest_handoff_observation_sequence",
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["manifest_handoff_attempts.attempt_id"],
            name="fk_manifest_handoff_observation_attempt",
        ),
        sa.CheckConstraint(
            "length(observation_id)>0", name="ck_manifest_handoff_observation_present"
        ),
        sa.CheckConstraint(
            "sequence_number>0", name="ck_manifest_handoff_observation_sequence"
        ),
        sa.CheckConstraint(
            "kind IN ('reserved','writer_started','writer_handed_off',"
            "'writer_outcome_unknown','manifest_absent','manifest_temporary_only',"
            "'manifest_handed_off','manifest_handed_off_pending_cleanup',"
            "'manifest_handoff_conflict','cleanup_completed','cleanup_outcome_unknown')",
            name="ck_manifest_handoff_observation_kind",
        ),
        sa.CheckConstraint(
            "(manifest_sha256 IS NULL AND file_count IS NULL) OR "
            "(length(manifest_sha256)=64 AND file_count>0)",
            name="ck_manifest_handoff_observation_manifest_facts",
        ),
    )


def downgrade() -> None:
    op.drop_table("manifest_handoff_attempt_observations")
    op.drop_table("manifest_handoff_attempts")
    op.drop_table("manifest_handoff_registry_authorities")
    op.drop_table("manifest_handoff_registry_scopes")
