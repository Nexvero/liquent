"""Add durable manifest-handoff supervisor journal foundations.

Revision ID: 20260824_0031
Revises: 20260824_0030
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260824_0031"
down_revision: str | Sequence[str] | None = "20260824_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_check(column: str, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(f"length({column})>0", name=name)


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_supervisor_journal_jobs",
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("backend_instance_id", sa.LargeBinary(), nullable=False),
        sa.Column("prepare_id", sa.LargeBinary(), nullable=False),
        sa.Column("launch_commit_id", sa.LargeBinary(), nullable=False),
        sa.Column("capability", sa.String(length=8), nullable=False),
        sa.Column("execution_claim_id", sa.LargeBinary(), nullable=True),
        sa.Column("recovery_claim_id", sa.LargeBinary(), nullable=True),
        sa.Column("owner_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("source_root", sa.Text(), nullable=False),
        sa.Column("target_root", sa.Text(), nullable=False),
        sa.Column("handoff_name", sa.String(length=128), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "handle_id", name="pk_manifest_handoff_supervisor_journal_jobs"
        ),
        sa.UniqueConstraint(
            "prepare_id", name="uq_manifest_handoff_supervisor_journal_prepare"
        ),
        sa.UniqueConstraint(
            "launch_commit_id", name="uq_manifest_handoff_supervisor_journal_launch"
        ),
        sa.UniqueConstraint(
            "handle_id",
            "capability",
            name="uq_manifest_handoff_supervisor_journal_handle_capability",
        ),
        _id_check("handle_id", "ck_manifest_handoff_supervisor_journal_handle"),
        _id_check("backend_instance_id", "ck_manifest_handoff_supervisor_journal_backend"),
        _id_check("prepare_id", "ck_manifest_handoff_supervisor_journal_prepare"),
        _id_check("launch_commit_id", "ck_manifest_handoff_supervisor_journal_launch"),
        _id_check("owner_id", "ck_manifest_handoff_supervisor_journal_owner"),
        _id_check("scope_id", "ck_manifest_handoff_supervisor_journal_scope"),
        sa.CheckConstraint(
            "(capability='writer' AND execution_claim_id IS NOT NULL "
            "AND recovery_claim_id IS NULL) OR "
            "(capability='recovery' AND execution_claim_id IS NULL "
            "AND recovery_claim_id IS NOT NULL)",
            name="ck_manifest_handoff_supervisor_journal_capability_claim",
        ),
        sa.CheckConstraint(
            "length(source_root)>0 AND length(target_root)>0 AND length(handoff_name)>0",
            name="ck_manifest_handoff_supervisor_journal_process_binding",
        ),
    )
    op.create_table(
        "manifest_handoff_supervisor_journal_transitions",
        sa.Column("transition_id", sa.LargeBinary(), nullable=False),
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("capability", sa.String(length=8), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("outcome_kind", sa.String(length=48), nullable=True),
        sa.Column("filename", sa.String(length=133), nullable=True),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "transition_id", name="pk_manifest_handoff_supervisor_journal_transitions"
        ),
        sa.UniqueConstraint(
            "handle_id", "sequence_number",
            name="uq_manifest_handoff_supervisor_journal_sequence",
        ),
        sa.UniqueConstraint(
            "handle_id", "kind",
            name="uq_manifest_handoff_supervisor_journal_kind",
        ),
        sa.ForeignKeyConstraint(
            ["handle_id", "capability"],
            [
                "manifest_handoff_supervisor_journal_jobs.handle_id",
                "manifest_handoff_supervisor_journal_jobs.capability",
            ],
            name="fk_manifest_handoff_supervisor_journal_transition_job",
        ),
        _id_check("transition_id", "ck_manifest_handoff_supervisor_journal_transition"),
        sa.CheckConstraint(
            "sequence_number>0", name="ck_manifest_handoff_supervisor_journal_sequence"
        ),
        sa.CheckConstraint(
            "kind IN ('launch_committed','prepared_gated','release_committed',"
            "'running','termination_requested','terminal_observed')",
            name="ck_manifest_handoff_supervisor_journal_transition_kind",
        ),
        sa.CheckConstraint(
            "(kind<>'terminal_observed' AND outcome_kind IS NULL AND filename IS NULL "
            "AND manifest_sha256 IS NULL AND file_count IS NULL) OR "
            "(kind='terminal_observed' AND outcome_kind IS NOT NULL)",
            name="ck_manifest_handoff_supervisor_journal_terminal_payload",
        ),
        sa.CheckConstraint(
            "(manifest_sha256 IS NULL AND file_count IS NULL) OR "
            "(length(manifest_sha256)=64 AND file_count>0)",
            name="ck_manifest_handoff_supervisor_journal_manifest_facts",
        ),
        sa.CheckConstraint(
            "(capability='writer' AND outcome_kind IN "
            "('manifest_handed_off','target_not_absent','source_not_stable',"
            "'outcome_unknown','unavailable')) OR "
            "(capability='recovery' AND outcome_kind IN "
            "('manifest_absent','manifest_temporary_only','manifest_handed_off',"
            "'manifest_handed_off_pending_cleanup','manifest_handoff_conflict',"
            "'outcome_unknown')) OR outcome_kind IS NULL",
            name="ck_manifest_handoff_supervisor_journal_outcome_capability",
        ),
        sa.CheckConstraint(
            "(outcome_kind='manifest_handed_off' AND filename IS NOT NULL "
            "AND manifest_sha256 IS NOT NULL AND file_count IS NOT NULL) OR "
            "(outcome_kind='manifest_handed_off_pending_cleanup' "
            "AND filename IS NOT NULL AND manifest_sha256 IS NOT NULL "
            "AND file_count IS NOT NULL) OR "
            "(outcome_kind='manifest_temporary_only' AND filename IS NULL "
            "AND manifest_sha256 IS NOT NULL AND file_count IS NOT NULL) OR "
            "(outcome_kind IS NOT NULL AND outcome_kind NOT IN "
            "('manifest_handed_off','manifest_handed_off_pending_cleanup',"
            "'manifest_temporary_only') AND filename IS NULL "
            "AND manifest_sha256 IS NULL AND file_count IS NULL) OR "
            "(outcome_kind IS NULL AND filename IS NULL "
            "AND manifest_sha256 IS NULL AND file_count IS NULL)",
            name="ck_manifest_handoff_supervisor_journal_outcome_facts",
        ),
    )


def downgrade() -> None:
    op.drop_table("manifest_handoff_supervisor_journal_transitions")
    op.drop_table("manifest_handoff_supervisor_journal_jobs")
