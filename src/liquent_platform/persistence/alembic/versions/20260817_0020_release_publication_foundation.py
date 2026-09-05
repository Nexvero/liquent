"""Add empty release-publication handoff foundation.

Revision ID: 20260817_0020
Revises: 20260817_0019
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0020"
down_revision: str | Sequence[str] | None = "20260817_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_publication_channels",
        sa.Column("channel_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("channel_id", name="pk_release_publication_channels"),
        sa.CheckConstraint("length(channel_id)>0", name="ck_release_channel_present"),
    )
    op.create_table(
        "release_publisher_authorities",
        sa.Column("authority_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("authority_id", name="pk_release_publishers"),
        sa.CheckConstraint("length(authority_id)>0", name="ck_release_publisher_present"),
    )
    op.create_table(
        "release_publication_channel_revisions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("channel_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("artifact_class", sa.String(length=32), nullable=False),
        sa.Column("package_name", sa.String(length=64), nullable=False),
        sa.Column("provider_kind", sa.String(length=32), nullable=False),
        sa.Column("target_name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name="pk_release_channel_revisions"),
        sa.UniqueConstraint("revision_id", "channel_id", name="uq_release_channel_revision"),
        sa.ForeignKeyConstraint(["channel_id"], ["release_publication_channels.channel_id"], name="fk_release_channel_revision_channel"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_release_channel_status"),
        sa.CheckConstraint("artifact_class='operational_bundle'", name="ck_release_channel_artifact_class"),
        sa.CheckConstraint("length(package_name)>0", name="ck_release_channel_package"),
        sa.CheckConstraint("length(provider_kind)>0", name="ck_release_channel_provider"),
        sa.CheckConstraint("length(target_name)>0", name="ck_release_channel_target"),
    )
    op.create_table(
        "release_publication_revision_publishers",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("channel_id", sa.LargeBinary(), nullable=False),
        sa.Column("authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", "authority_id", name="pk_release_revision_publishers"),
        sa.ForeignKeyConstraint(["revision_id", "channel_id"], ["release_publication_channel_revisions.revision_id", "release_publication_channel_revisions.channel_id"], name="fk_release_revision_publisher_revision", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["authority_id"], ["release_publisher_authorities.authority_id"], name="fk_release_revision_publisher_authority"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_release_revision_publisher_status"),
    )
    op.create_table(
        "release_publication_current_channels",
        sa.Column("channel_id", sa.LargeBinary(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("channel_id", name="pk_release_current_channels"),
        sa.ForeignKeyConstraint(["revision_id", "channel_id"], ["release_publication_channel_revisions.revision_id", "release_publication_channel_revisions.channel_id"], name="fk_release_current_channel_revision"),
    )
    op.create_table(
        "release_publication_handoffs",
        sa.Column("handoff_id", sa.LargeBinary(), nullable=False),
        sa.Column("decision_id", sa.LargeBinary(), nullable=False),
        sa.Column("publisher_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("channel_id", sa.LargeBinary(), nullable=False),
        sa.Column("channel_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("bundle_sha256", sa.String(length=64), nullable=False),
        sa.Column("wheel_sha256", sa.String(length=64), nullable=False),
        sa.Column("checksums_sha256", sa.String(length=64), nullable=False),
        sa.Column("signature_sha256", sa.String(length=64), nullable=False),
        sa.Column("promotion_evidence_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_commit", sa.String(length=40), nullable=False),
        sa.Column("package_version", sa.String(length=64), nullable=False),
        sa.Column("bundle_format_version", sa.Integer(), nullable=False),
        sa.Column("signer_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.LargeBinary(), nullable=False),
        sa.Column("registry_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("policy_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("promotion_verifier_id", sa.LargeBinary(), nullable=False),
        sa.Column("promotion_decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.PrimaryKeyConstraint("handoff_id", name="pk_release_publication_handoffs"),
        sa.UniqueConstraint("decision_id", name="uq_release_publication_decision"),
        sa.ForeignKeyConstraint(["publisher_authority_id"], ["release_publisher_authorities.authority_id"], name="fk_release_handoff_publisher"),
        sa.ForeignKeyConstraint(["channel_revision_id", "channel_id"], ["release_publication_channel_revisions.revision_id", "release_publication_channel_revisions.channel_id"], name="fk_release_handoff_channel_revision"),
        sa.ForeignKeyConstraint(["key_id", "signer_authority_id"], ["release_signing_keys.key_id", "release_signing_keys.signer_authority_id"], name="fk_release_handoff_signing_key"),
        sa.ForeignKeyConstraint(["registry_revision_id"], ["release_registry_set_revisions.revision_id"], name="fk_release_handoff_registry_revision"),
        sa.CheckConstraint("status='ready_for_publication'", name="ck_release_handoff_status"),
        sa.CheckConstraint("bundle_format_version>0", name="ck_release_handoff_bundle_format"),
    )
    op.create_table(
        "release_publication_receipts",
        sa.Column("receipt_id", sa.LargeBinary(), nullable=False),
        sa.Column("handoff_id", sa.LargeBinary(), nullable=False),
        sa.Column("provider_receipt", sa.LargeBinary(), nullable=False),
        sa.Column("observed_bundle_sha256", sa.String(length=64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("receipt_id", name="pk_release_publication_receipts"),
        sa.UniqueConstraint("handoff_id", name="uq_release_publication_receipt_handoff"),
        sa.ForeignKeyConstraint(["handoff_id"], ["release_publication_handoffs.handoff_id"], name="fk_release_receipt_handoff"),
        sa.CheckConstraint("length(provider_receipt)>0", name="ck_release_provider_receipt_present"),
    )
    op.create_table(
        "release_publication_reassessments",
        sa.Column("reassessment_id", sa.LargeBinary(), nullable=False),
        sa.Column("handoff_id", sa.LargeBinary(), nullable=False),
        sa.Column("intent", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("reassessment_id", name="pk_release_publication_reassessments"),
        sa.ForeignKeyConstraint(["handoff_id"], ["release_publication_handoffs.handoff_id"], name="fk_release_reassessment_handoff"),
        sa.CheckConstraint("intent IN ('reassess','withdraw')", name="ck_release_reassessment_intent"),
        sa.CheckConstraint("status IN ('pending','completed')", name="ck_release_reassessment_status"),
    )


def downgrade() -> None:
    op.drop_table("release_publication_reassessments")
    op.drop_table("release_publication_receipts")
    op.drop_table("release_publication_handoffs")
    op.drop_table("release_publication_current_channels")
    op.drop_table("release_publication_revision_publishers")
    op.drop_table("release_publication_channel_revisions")
    op.drop_table("release_publisher_authorities")
    op.drop_table("release_publication_channels")
