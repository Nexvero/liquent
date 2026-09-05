"""Add persistent manifest-handoff supervisor correlation foundations.

Revision ID: 20260824_0030
Revises: 20260824_0029
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260824_0030"
down_revision: str | Sequence[str] | None = "20260824_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_check(column: str, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(f"length({column})>0", name=name)


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_supervisor_backends",
        sa.Column("backend_instance_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("provisioned_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "backend_instance_id", name="pk_manifest_handoff_supervisor_backends"
        ),
        _id_check(
            "backend_instance_id", "ck_manifest_handoff_supervisor_backend_present"
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive')",
            name="ck_manifest_handoff_supervisor_backend_status",
        ),
    )
    op.create_table(
        "manifest_handoff_supervisor_preparations",
        sa.Column("prepare_id", sa.LargeBinary(), nullable=False),
        sa.Column("backend_instance_id", sa.LargeBinary(), nullable=False),
        sa.Column("capability", sa.String(length=8), nullable=False),
        sa.Column("execution_claim_id", sa.LargeBinary(), nullable=True),
        sa.Column("recovery_claim_id", sa.LargeBinary(), nullable=True),
        sa.Column("owner_id", sa.LargeBinary(), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "prepare_id", name="pk_manifest_handoff_supervisor_preparations"
        ),
        sa.UniqueConstraint(
            "execution_claim_id", name="uq_manifest_handoff_supervisor_execution_claim"
        ),
        sa.UniqueConstraint(
            "recovery_claim_id", name="uq_manifest_handoff_supervisor_recovery_claim"
        ),
        sa.UniqueConstraint(
            "prepare_id",
            "backend_instance_id",
            name="uq_manifest_handoff_supervisor_prepare_backend",
        ),
        sa.ForeignKeyConstraint(
            ["backend_instance_id"],
            ["manifest_handoff_supervisor_backends.backend_instance_id"],
            name="fk_manifest_handoff_supervisor_prepare_backend",
        ),
        sa.ForeignKeyConstraint(
            ["execution_claim_id"],
            ["manifest_handoff_execution_claims.claim_id"],
            name="fk_manifest_handoff_supervisor_prepare_execution_claim",
        ),
        sa.ForeignKeyConstraint(
            ["recovery_claim_id"],
            ["manifest_handoff_recovery_claims.claim_id"],
            name="fk_manifest_handoff_supervisor_prepare_recovery_claim",
        ),
        _id_check("prepare_id", "ck_manifest_handoff_supervisor_prepare_present"),
        _id_check("owner_id", "ck_manifest_handoff_supervisor_owner_present"),
        sa.CheckConstraint(
            "(capability='writer' AND execution_claim_id IS NOT NULL "
            "AND recovery_claim_id IS NULL) OR "
            "(capability='recovery' AND execution_claim_id IS NULL "
            "AND recovery_claim_id IS NOT NULL)",
            name="ck_manifest_handoff_supervisor_prepare_capability_claim",
        ),
    )
    op.create_table(
        "manifest_handoff_supervisor_handle_bindings",
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("prepare_id", sa.LargeBinary(), nullable=False),
        sa.Column("backend_instance_id", sa.LargeBinary(), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "handle_id", name="pk_manifest_handoff_supervisor_handle_bindings"
        ),
        sa.UniqueConstraint(
            "prepare_id", name="uq_manifest_handoff_supervisor_handle_prepare"
        ),
        sa.UniqueConstraint(
            "backend_instance_id",
            "handle_id",
            name="uq_manifest_handoff_supervisor_backend_handle",
        ),
        sa.ForeignKeyConstraint(
            ["prepare_id", "backend_instance_id"],
            [
                "manifest_handoff_supervisor_preparations.prepare_id",
                "manifest_handoff_supervisor_preparations.backend_instance_id",
            ],
            name="fk_manifest_handoff_supervisor_handle_prepare_backend",
        ),
        sa.ForeignKeyConstraint(
            ["backend_instance_id"],
            ["manifest_handoff_supervisor_backends.backend_instance_id"],
            name="fk_manifest_handoff_supervisor_handle_backend",
        ),
        _id_check("handle_id", "ck_manifest_handoff_supervisor_handle_present"),
    )
    op.create_table(
        "manifest_handoff_supervisor_releases",
        sa.Column("release_id", sa.LargeBinary(), nullable=False),
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "release_id", name="pk_manifest_handoff_supervisor_releases"
        ),
        sa.UniqueConstraint(
            "handle_id", name="uq_manifest_handoff_supervisor_release_handle"
        ),
        sa.ForeignKeyConstraint(
            ["handle_id"],
            ["manifest_handoff_supervisor_handle_bindings.handle_id"],
            name="fk_manifest_handoff_supervisor_release_handle",
        ),
        _id_check("release_id", "ck_manifest_handoff_supervisor_release_present"),
    )
    op.create_table(
        "manifest_handoff_supervisor_terminations",
        sa.Column("terminate_id", sa.LargeBinary(), nullable=False),
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "terminate_id", name="pk_manifest_handoff_supervisor_terminations"
        ),
        sa.UniqueConstraint(
            "handle_id", name="uq_manifest_handoff_supervisor_terminate_handle"
        ),
        sa.ForeignKeyConstraint(
            ["handle_id"],
            ["manifest_handoff_supervisor_handle_bindings.handle_id"],
            name="fk_manifest_handoff_supervisor_terminate_handle",
        ),
        _id_check("terminate_id", "ck_manifest_handoff_supervisor_terminate_present"),
    )
    op.create_table(
        "manifest_handoff_supervisor_terminal_observations",
        sa.Column("terminal_observation_id", sa.LargeBinary(), nullable=False),
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "terminal_observation_id",
            name="pk_manifest_handoff_supervisor_terminal_observations",
        ),
        sa.UniqueConstraint(
            "handle_id", name="uq_manifest_handoff_supervisor_terminal_handle"
        ),
        sa.ForeignKeyConstraint(
            ["handle_id"],
            ["manifest_handoff_supervisor_handle_bindings.handle_id"],
            name="fk_manifest_handoff_supervisor_terminal_handle",
        ),
        _id_check(
            "terminal_observation_id",
            "ck_manifest_handoff_supervisor_terminal_observation_present",
        ),
    )


def downgrade() -> None:
    op.drop_table("manifest_handoff_supervisor_terminal_observations")
    op.drop_table("manifest_handoff_supervisor_terminations")
    op.drop_table("manifest_handoff_supervisor_releases")
    op.drop_table("manifest_handoff_supervisor_handle_bindings")
    op.drop_table("manifest_handoff_supervisor_preparations")
    op.drop_table("manifest_handoff_supervisor_backends")
