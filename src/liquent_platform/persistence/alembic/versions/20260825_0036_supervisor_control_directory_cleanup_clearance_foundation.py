"""Add supervisor control-directory cleanup clearance foundations.

Revision ID: 20260825_0036
Revises: 20260825_0035
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260825_0036"
down_revision: str | Sequence[str] | None = "20260825_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_check(column: str, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(f"length({column})>0", name=name)


def _target_revision_table(kind: str) -> None:
    table = f"manifest_handoff_supervisor_cleanup_{kind}_revisions"
    prefix = f"mh_supervisor_cleanup_{kind}"
    op.create_table(
        table,
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("directory_id", sa.LargeBinary(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("disposition", sa.String(length=7), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name=f"pk_{prefix}_revisions"),
        sa.UniqueConstraint(
            "revision_id", "directory_id", name=f"uq_{prefix}_binding"
        ),
        sa.UniqueConstraint(
            "directory_id", "sequence_number", name=f"uq_{prefix}_sequence"
        ),
        sa.ForeignKeyConstraint(
            ["directory_id"],
            ["manifest_handoff_supervisor_control_directories.directory_id"],
            name=f"fk_{prefix}_directory",
        ),
        _id_check("revision_id", f"ck_{prefix}_revision_id"),
        sa.CheckConstraint(
            "sequence_number>0", name=f"ck_{prefix}_sequence"
        ),
        sa.CheckConstraint(
            "disposition IN ('clear','blocked')",
            name=f"ck_{prefix}_disposition",
        ),
    )


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_supervisor_cleanup_management_revisions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", name="pk_mh_supervisor_cleanup_management_revisions"
        ),
        sa.UniqueConstraint(
            "revision_id", "actor_user_id", "scope_id",
            name="uq_mh_supervisor_cleanup_management_binding",
        ),
        sa.UniqueConstraint(
            "actor_user_id", "scope_id", "sequence_number",
            name="uq_mh_supervisor_cleanup_management_sequence",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_mh_supervisor_cleanup_management_actor",
        ),
        sa.ForeignKeyConstraint(
            ["scope_id"], ["manifest_handoff_registry_scopes.scope_id"],
            name="fk_mh_supervisor_cleanup_management_scope",
        ),
        _id_check("revision_id", "ck_mh_supervisor_cleanup_management_revision"),
        sa.CheckConstraint(
            "sequence_number>0", name="ck_mh_supervisor_cleanup_management_sequence"
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive')",
            name="ck_mh_supervisor_cleanup_management_status",
        ),
    )
    _target_revision_table("hold")
    _target_revision_table("recovery")
    _target_revision_table("reference")
    op.create_table(
        "manifest_handoff_supervisor_cleanup_clearances",
        sa.Column("clearance_id", sa.LargeBinary(), nullable=False),
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("directory_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("terminal_observation_id", sa.LargeBinary(), nullable=False),
        sa.Column("decision_id", sa.LargeBinary(), nullable=False),
        sa.Column("management_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("hold_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("recovery_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("reference_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "clearance_id", name="pk_mh_supervisor_cleanup_clearances"
        ),
        sa.UniqueConstraint(
            "attempt_id", name="uq_mh_supervisor_cleanup_clearance_attempt"
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["manifest_handoff_supervisor_control_cleanup_attempts.attempt_id"],
            name="fk_mh_supervisor_cleanup_clearance_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["decision_id", "directory_id"],
            [
                "manifest_handoff_supervisor_control_cleanup_decisions.decision_id",
                "manifest_handoff_supervisor_control_cleanup_decisions.directory_id",
            ],
            name="fk_mh_supervisor_cleanup_clearance_decision",
        ),
        sa.ForeignKeyConstraint(
            ["management_revision_id", "actor_user_id", "scope_id"],
            [
                "manifest_handoff_supervisor_cleanup_management_revisions.revision_id",
                "manifest_handoff_supervisor_cleanup_management_revisions.actor_user_id",
                "manifest_handoff_supervisor_cleanup_management_revisions.scope_id",
            ],
            name="fk_mh_supervisor_cleanup_clearance_management",
        ),
        sa.ForeignKeyConstraint(
            ["hold_revision_id", "directory_id"],
            [
                "manifest_handoff_supervisor_cleanup_hold_revisions.revision_id",
                "manifest_handoff_supervisor_cleanup_hold_revisions.directory_id",
            ],
            name="fk_mh_supervisor_cleanup_clearance_hold",
        ),
        sa.ForeignKeyConstraint(
            ["recovery_revision_id", "directory_id"],
            [
                "manifest_handoff_supervisor_cleanup_recovery_revisions.revision_id",
                "manifest_handoff_supervisor_cleanup_recovery_revisions.directory_id",
            ],
            name="fk_mh_supervisor_cleanup_clearance_recovery",
        ),
        sa.ForeignKeyConstraint(
            ["reference_revision_id", "directory_id"],
            [
                "manifest_handoff_supervisor_cleanup_reference_revisions.revision_id",
                "manifest_handoff_supervisor_cleanup_reference_revisions.directory_id",
            ],
            name="fk_mh_supervisor_cleanup_clearance_reference",
        ),
        sa.ForeignKeyConstraint(
            ["terminal_observation_id"],
            ["manifest_handoff_supervisor_terminal_observations.terminal_observation_id"],
            name="fk_mh_supervisor_cleanup_clearance_terminal",
        ),
        _id_check("clearance_id", "ck_mh_supervisor_cleanup_clearance_id"),
    )


def downgrade() -> None:
    op.drop_table("manifest_handoff_supervisor_cleanup_clearances")
    op.drop_table("manifest_handoff_supervisor_cleanup_reference_revisions")
    op.drop_table("manifest_handoff_supervisor_cleanup_recovery_revisions")
    op.drop_table("manifest_handoff_supervisor_cleanup_hold_revisions")
    op.drop_table("manifest_handoff_supervisor_cleanup_management_revisions")
