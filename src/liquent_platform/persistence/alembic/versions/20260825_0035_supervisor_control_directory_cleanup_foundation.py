"""Add supervisor control-directory cleanup decision and attempt foundation.

Revision ID: 20260825_0035
Revises: 20260825_0034
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260825_0035"
down_revision: str | Sequence[str] | None = "20260825_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_check(column: str, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(f"length({column})>0", name=name)


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_supervisor_control_cleanup_decisions",
        sa.Column("decision_id", sa.LargeBinary(), nullable=False),
        sa.Column("directory_id", sa.LargeBinary(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("policy_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("disposition", sa.String(length=8), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "decision_id", name="pk_mh_supervisor_control_cleanup_decisions"
        ),
        sa.UniqueConstraint(
            "decision_id", "directory_id",
            name="uq_mh_supervisor_control_cleanup_decision_binding",
        ),
        sa.UniqueConstraint(
            "directory_id", "sequence_number",
            name="uq_mh_supervisor_control_cleanup_decision_sequence",
        ),
        sa.ForeignKeyConstraint(
            ["directory_id"],
            ["manifest_handoff_supervisor_control_directories.directory_id"],
            name="fk_mh_supervisor_control_cleanup_decision_directory",
        ),
        _id_check("decision_id", "ck_mh_supervisor_control_cleanup_decision_id"),
        _id_check(
            "policy_revision_id", "ck_mh_supervisor_control_cleanup_policy_revision"
        ),
        sa.CheckConstraint(
            "sequence_number>0",
            name="ck_mh_supervisor_control_cleanup_decision_sequence",
        ),
        sa.CheckConstraint(
            "disposition IN ('retain','eligible')",
            name="ck_mh_supervisor_control_cleanup_disposition",
        ),
    )
    op.create_table(
        "manifest_handoff_supervisor_control_cleanup_attempts",
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("directory_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("decision_id", sa.LargeBinary(), nullable=False),
        sa.Column("state", sa.String(length=15), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unknown_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=14), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciliation_outcome", sa.String(length=8), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint(
            "attempt_id", name="pk_mh_supervisor_control_cleanup_attempts"
        ),
        sa.ForeignKeyConstraint(
            ["decision_id", "directory_id"],
            [
                "manifest_handoff_supervisor_control_cleanup_decisions.decision_id",
                "manifest_handoff_supervisor_control_cleanup_decisions.directory_id",
            ],
            name="fk_mh_supervisor_control_cleanup_attempt_decision",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_mh_supervisor_control_cleanup_attempt_actor",
        ),
        _id_check("attempt_id", "ck_mh_supervisor_control_cleanup_attempt_id"),
        sa.CheckConstraint(
            "state IN ('started','outcome_unknown','completed','reconciled')",
            name="ck_mh_supervisor_control_cleanup_attempt_state",
        ),
        sa.CheckConstraint(
            "(state='started' AND unknown_at IS NULL AND outcome IS NULL "
            "AND completed_at IS NULL AND reconciliation_outcome IS NULL "
            "AND reconciled_at IS NULL) OR "
            "(state='outcome_unknown' AND unknown_at IS NOT NULL "
            "AND outcome IS NULL AND completed_at IS NULL "
            "AND reconciliation_outcome IS NULL AND reconciled_at IS NULL) OR "
            "(state='completed' AND unknown_at IS NULL "
            "AND outcome IN ('removed','already_absent') "
            "AND completed_at IS NOT NULL AND reconciliation_outcome IS NULL "
            "AND reconciled_at IS NULL) OR "
            "(state='reconciled' AND unknown_at IS NOT NULL "
            "AND outcome IS NULL AND completed_at IS NULL "
            "AND reconciliation_outcome IN ('absent','present','conflict') "
            "AND reconciled_at IS NOT NULL)",
            name="ck_mh_supervisor_control_cleanup_attempt_state_values",
        ),
        sa.CheckConstraint(
            "unknown_at IS NULL OR unknown_at>=started_at",
            name="ck_mh_supervisor_control_cleanup_attempt_unknown_order",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at>=started_at",
            name="ck_mh_supervisor_control_cleanup_attempt_complete_order",
        ),
        sa.CheckConstraint(
            "reconciled_at IS NULL OR reconciled_at>=unknown_at",
            name="ck_mh_supervisor_control_cleanup_attempt_reconcile_order",
        ),
    )
    op.create_index(
        "uq_mh_supervisor_control_cleanup_unresolved_directory",
        "manifest_handoff_supervisor_control_cleanup_attempts",
        ["directory_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('started','outcome_unknown')"),
        sqlite_where=sa.text("state IN ('started','outcome_unknown')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_mh_supervisor_control_cleanup_unresolved_directory",
        table_name="manifest_handoff_supervisor_control_cleanup_attempts",
    )
    op.drop_table("manifest_handoff_supervisor_control_cleanup_attempts")
    op.drop_table("manifest_handoff_supervisor_control_cleanup_decisions")
