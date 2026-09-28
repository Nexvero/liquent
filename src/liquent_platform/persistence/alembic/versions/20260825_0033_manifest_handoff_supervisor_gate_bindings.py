"""Add immutable supervisor gate-binding reservations.

Revision ID: 20260825_0033
Revises: 20260824_0032
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260825_0033"
down_revision: str | Sequence[str] | None = "20260824_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_check(column: str, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(f"length({column})>0", name=name)


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_supervisor_gate_bindings",
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("profile", sa.String(length=8), nullable=False),
        sa.Column("gated_observation_id", sa.LargeBinary(), nullable=False),
        sa.Column("terminal_observation_id", sa.LargeBinary(), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "handle_id", name="pk_manifest_handoff_supervisor_gate_bindings"
        ),
        sa.UniqueConstraint(
            "gated_observation_id",
            name="uq_manifest_handoff_supervisor_gate_gated_observation",
        ),
        sa.UniqueConstraint(
            "terminal_observation_id",
            name="uq_manifest_handoff_supervisor_gate_terminal_observation",
        ),
        sa.ForeignKeyConstraint(
            ["handle_id"],
            ["manifest_handoff_supervisor_runtime_bindings.handle_id"],
            name="fk_manifest_handoff_supervisor_gate_runtime",
        ),
        sa.CheckConstraint(
            "profile IN ('writer','recovery')",
            name="ck_manifest_handoff_supervisor_gate_profile",
        ),
        _id_check(
            "gated_observation_id",
            "ck_manifest_handoff_supervisor_gate_gated_observation",
        ),
        _id_check(
            "terminal_observation_id",
            "ck_manifest_handoff_supervisor_gate_terminal_observation",
        ),
        sa.CheckConstraint(
            "gated_observation_id<>terminal_observation_id",
            name="ck_manifest_handoff_supervisor_gate_distinct_observations",
        ),
    )
    op.create_table(
        "manifest_handoff_supervisor_gate_artifact_reservations",
        sa.Column("artifact_id", sa.LargeBinary(), nullable=False),
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("role", sa.String(length=18), nullable=False),
        sa.PrimaryKeyConstraint(
            "artifact_id",
            name="pk_manifest_handoff_supervisor_gate_artifact_reservations",
        ),
        sa.UniqueConstraint(
            "handle_id", "role",
            name="uq_manifest_handoff_supervisor_gate_artifact_role",
        ),
        sa.ForeignKeyConstraint(
            ["handle_id"],
            ["manifest_handoff_supervisor_gate_bindings.handle_id"],
            name="fk_manifest_handoff_supervisor_gate_artifact_binding",
        ),
        _id_check(
            "artifact_id", "ck_manifest_handoff_supervisor_gate_artifact_id"
        ),
        sa.CheckConstraint(
            "role IN ('wrapper_ready','release_consumed','terminal_envelope')",
            name="ck_manifest_handoff_supervisor_gate_artifact_role",
        ),
    )


def downgrade() -> None:
    op.drop_table("manifest_handoff_supervisor_gate_artifact_reservations")
    op.drop_table("manifest_handoff_supervisor_gate_bindings")
