"""Add Docker runtime and private control-artifact correlation foundations.

Revision ID: 20260824_0032
Revises: 20260824_0031
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260824_0032"
down_revision: str | Sequence[str] | None = "20260824_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_check(column: str, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(f"length({column})>0", name=name)


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_supervisor_runtime_bindings",
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("creation_id", sa.LargeBinary(), nullable=False),
        sa.Column("runtime_container_id", sa.LargeBinary(), nullable=False),
        sa.Column("control_directory_id", sa.LargeBinary(), nullable=False),
        sa.Column("image_digest", sa.String(length=71), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "handle_id", name="pk_manifest_handoff_supervisor_runtime_bindings"
        ),
        sa.UniqueConstraint(
            "creation_id", name="uq_manifest_handoff_supervisor_runtime_creation"
        ),
        sa.UniqueConstraint(
            "runtime_container_id",
            name="uq_manifest_handoff_supervisor_runtime_container",
        ),
        sa.UniqueConstraint(
            "control_directory_id",
            name="uq_manifest_handoff_supervisor_runtime_control_directory",
        ),
        sa.ForeignKeyConstraint(
            ["handle_id"],
            ["manifest_handoff_supervisor_journal_jobs.handle_id"],
            name="fk_manifest_handoff_supervisor_runtime_job",
        ),
        _id_check("creation_id", "ck_manifest_handoff_supervisor_runtime_creation"),
        _id_check(
            "runtime_container_id", "ck_manifest_handoff_supervisor_runtime_container"
        ),
        _id_check(
            "control_directory_id", "ck_manifest_handoff_supervisor_runtime_control"
        ),
        sa.CheckConstraint(
            "length(image_digest)=71 AND substr(image_digest,1,7)='sha256:'",
            name="ck_manifest_handoff_supervisor_runtime_image_digest",
        ),
    )
    op.create_table(
        "manifest_handoff_supervisor_control_artifacts",
        sa.Column("artifact_id", sa.LargeBinary(), nullable=False),
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("correlation_id", sa.LargeBinary(), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "artifact_id", name="pk_manifest_handoff_supervisor_control_artifacts"
        ),
        sa.UniqueConstraint(
            "handle_id", "role",
            name="uq_manifest_handoff_supervisor_control_artifact_role",
        ),
        sa.ForeignKeyConstraint(
            ["handle_id"],
            ["manifest_handoff_supervisor_runtime_bindings.handle_id"],
            name="fk_manifest_handoff_supervisor_control_artifact_runtime",
        ),
        _id_check("artifact_id", "ck_manifest_handoff_supervisor_control_artifact"),
        _id_check(
            "correlation_id", "ck_manifest_handoff_supervisor_control_correlation"
        ),
        sa.CheckConstraint(
            "role IN ('wrapper_ready','release_token','release_consumed',"
            "'terminal_envelope')",
            name="ck_manifest_handoff_supervisor_control_artifact_role",
        ),
        sa.CheckConstraint(
            "length(artifact_sha256)=64 AND byte_count>0",
            name="ck_manifest_handoff_supervisor_control_artifact_facts",
        ),
    )


def downgrade() -> None:
    op.drop_table("manifest_handoff_supervisor_control_artifacts")
    op.drop_table("manifest_handoff_supervisor_runtime_bindings")
