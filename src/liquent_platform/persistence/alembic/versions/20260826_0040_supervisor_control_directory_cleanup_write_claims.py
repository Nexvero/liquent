"""Add durable supervisor control-directory cleanup write claims.

Revision ID: 20260826_0040
Revises: 20260826_0039
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0040"
down_revision: str | Sequence[str] | None = "20260826_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ATTEMPTS = "manifest_handoff_supervisor_control_cleanup_attempts"
_CLEARANCES = "manifest_handoff_supervisor_cleanup_clearances"
_CLAIMS = "manifest_handoff_supervisor_control_cleanup_write_claims"


def _state_values(include_claim: bool) -> str:
    states = "'started','outcome_unknown','completed','reconciled'"
    if include_claim:
        states = "'started','write_claimed','outcome_unknown','completed','reconciled'"
    return f"state IN ({states})"


def _lifecycle_values(include_claim: bool) -> str:
    claim_null = "write_claimed_at IS NULL AND " if include_claim else ""
    started = (
        f"(state='started' AND {claim_null}unknown_at IS NULL AND outcome IS NULL "
        "AND completed_at IS NULL AND reconciliation_outcome IS NULL AND reconciled_at IS NULL)"
    )
    if not include_claim:
        return (
            started + " OR (state='outcome_unknown' AND unknown_at IS NOT NULL AND outcome IS NULL "
            "AND completed_at IS NULL AND reconciliation_outcome IS NULL AND reconciled_at IS NULL) OR "
            "(state='completed' AND unknown_at IS NULL AND outcome IN ('removed','already_absent') "
            "AND completed_at IS NOT NULL AND reconciliation_outcome IS NULL AND reconciled_at IS NULL) OR "
            "(state='reconciled' AND unknown_at IS NOT NULL AND outcome IS NULL AND completed_at IS NULL "
            "AND reconciliation_outcome IN ('absent','present','conflict') AND reconciled_at IS NOT NULL)"
        )
    return (
        started + " OR (state='write_claimed' AND write_claimed_at IS NOT NULL AND unknown_at IS NULL "
        "AND outcome IS NULL AND completed_at IS NULL AND reconciliation_outcome IS NULL AND reconciled_at IS NULL) OR "
        "(state='outcome_unknown' AND write_claimed_at IS NOT NULL AND unknown_at IS NOT NULL "
        "AND outcome IS NULL AND completed_at IS NULL AND reconciliation_outcome IS NULL AND reconciled_at IS NULL) OR "
        "(state='completed' AND unknown_at IS NULL AND completed_at IS NOT NULL "
        "AND ((outcome='removed' AND write_claimed_at IS NOT NULL) OR "
        "(outcome='already_absent' AND write_claimed_at IS NULL)) "
        "AND reconciliation_outcome IS NULL AND reconciled_at IS NULL) OR "
        "(state='reconciled' AND write_claimed_at IS NOT NULL AND unknown_at IS NOT NULL "
        "AND outcome IS NULL AND completed_at IS NULL AND reconciliation_outcome IN ('absent','present','conflict') "
        "AND reconciled_at IS NOT NULL)"
    )


def upgrade() -> None:
    op.drop_index("uq_mh_supervisor_control_cleanup_unresolved_directory", table_name=_ATTEMPTS)
    with op.batch_alter_table(_ATTEMPTS) as batch:
        batch.add_column(sa.Column("write_claimed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_unique_constraint(
            "uq_mh_supervisor_control_cleanup_attempt_binding", ["attempt_id", "directory_id"]
        )
        batch.drop_constraint("ck_mh_supervisor_control_cleanup_attempt_state", type_="check")
        batch.drop_constraint("ck_mh_supervisor_control_cleanup_attempt_state_values", type_="check")
        batch.create_check_constraint(
            "ck_mh_supervisor_control_cleanup_attempt_state", _state_values(True)
        )
        batch.create_check_constraint(
            "ck_mh_supervisor_control_cleanup_attempt_state_values", _lifecycle_values(True)
        )
        batch.create_check_constraint(
            "ck_mh_supervisor_control_cleanup_attempt_claim_order",
            "write_claimed_at IS NULL OR write_claimed_at>=started_at",
        )
        batch.create_check_constraint(
            "ck_mh_supervisor_control_cleanup_attempt_unknown_claim_order",
            "unknown_at IS NULL OR unknown_at>=write_claimed_at",
        )
    with op.batch_alter_table(_CLEARANCES) as batch:
        batch.create_unique_constraint(
            "uq_mh_supervisor_cleanup_clearance_attempt_binding",
            ["clearance_id", "attempt_id", "directory_id"],
        )
    op.create_table(
        _CLAIMS,
        sa.Column("claim_id", sa.LargeBinary(), nullable=False),
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("directory_id", sa.LargeBinary(), nullable=False),
        sa.Column("clearance_id", sa.LargeBinary(), nullable=False),
        sa.Column("preflight_id", sa.LargeBinary(), nullable=False),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("claim_id", name="pk_mh_supervisor_control_cleanup_write_claims"),
        sa.UniqueConstraint("attempt_id", name="uq_mh_supervisor_control_cleanup_write_claim_attempt"),
        sa.UniqueConstraint("preflight_id", name="uq_mh_supervisor_control_cleanup_write_claim_preflight"),
        sa.ForeignKeyConstraint(
            ["attempt_id", "directory_id"], [f"{_ATTEMPTS}.attempt_id", f"{_ATTEMPTS}.directory_id"],
            name="fk_mh_supervisor_control_cleanup_write_claim_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["clearance_id", "attempt_id", "directory_id"],
            [f"{_CLEARANCES}.clearance_id", f"{_CLEARANCES}.attempt_id", f"{_CLEARANCES}.directory_id"],
            name="fk_mh_supervisor_control_cleanup_write_claim_clearance",
        ),
        sa.CheckConstraint("length(claim_id)>0", name="ck_mh_supervisor_control_cleanup_write_claim_id"),
        sa.CheckConstraint("length(preflight_id)>0", name="ck_mh_supervisor_control_cleanup_write_preflight_id"),
        sa.CheckConstraint("claimed_at>=prepared_at", name="ck_mh_supervisor_control_cleanup_write_claimed_order"),
    )
    op.create_index(
        "uq_mh_supervisor_control_cleanup_unresolved_directory", _ATTEMPTS, ["directory_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('started','write_claimed','outcome_unknown')"),
        sqlite_where=sa.text("state IN ('started','write_claimed','outcome_unknown')"),
    )


def downgrade() -> None:
    op.drop_index("uq_mh_supervisor_control_cleanup_unresolved_directory", table_name=_ATTEMPTS)
    op.drop_table(_CLAIMS)
    with op.batch_alter_table(_CLEARANCES) as batch:
        batch.drop_constraint("uq_mh_supervisor_cleanup_clearance_attempt_binding", type_="unique")
    with op.batch_alter_table(_ATTEMPTS) as batch:
        batch.drop_constraint("ck_mh_supervisor_control_cleanup_attempt_unknown_claim_order", type_="check")
        batch.drop_constraint("ck_mh_supervisor_control_cleanup_attempt_claim_order", type_="check")
        batch.drop_constraint("ck_mh_supervisor_control_cleanup_attempt_state_values", type_="check")
        batch.drop_constraint("ck_mh_supervisor_control_cleanup_attempt_state", type_="check")
        batch.drop_constraint("uq_mh_supervisor_control_cleanup_attempt_binding", type_="unique")
        batch.drop_column("write_claimed_at")
        batch.create_check_constraint(
            "ck_mh_supervisor_control_cleanup_attempt_state", _state_values(False)
        )
        batch.create_check_constraint(
            "ck_mh_supervisor_control_cleanup_attempt_state_values", _lifecycle_values(False)
        )
    op.create_index(
        "uq_mh_supervisor_control_cleanup_unresolved_directory", _ATTEMPTS, ["directory_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('started','outcome_unknown')"),
        sqlite_where=sa.text("state IN ('started','outcome_unknown')"),
    )
