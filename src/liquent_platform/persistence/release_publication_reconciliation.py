"""Read-only reconciliation of one possible external publication effect."""

from __future__ import annotations

from sqlalchemy import Engine, text

from liquent_platform.identity.ports import ReleasePublicationTargetInspector
from liquent_platform.identity.release_publication import (
    ReconciledReleasePublicationOutcome,
    ReleasePublicationAttemptId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationHandoffId,
    ReleasePublicationReconciliationKind,
    ReleasePublicationTarget,
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationReconciliationUnavailable,
)


_UNKNOWN = text(
    "SELECT execution.handoff_id,handoff.channel_id,handoff.channel_revision_id,"
    " channel.provider_kind,channel.target_name,channel.package_name,"
    " handoff.package_version,handoff.wheel_sha256"
    " FROM release_publication_executions execution"
    " JOIN release_publication_execution_attempts attempt"
    " ON attempt.execution_id=execution.execution_id"
    " JOIN release_publication_handoffs handoff"
    " ON handoff.handoff_id=execution.handoff_id"
    " JOIN release_publication_channel_revisions channel"
    " ON channel.revision_id=handoff.channel_revision_id"
    " AND channel.channel_id=handoff.channel_id"
    " WHERE execution.execution_id=:execution AND attempt.attempt_id=:attempt"
    " AND execution.status='outcome_unknown'"
    " AND attempt.status='outcome_unknown' AND attempt.finished_at IS NULL"
    " AND (attempt.attempt_number=1 OR"
    " (attempt.attempt_number=2 AND EXISTS"
    " (SELECT 1 FROM release_publication_execution_attempts recovered"
    " JOIN release_publication_recovery_decisions recovery"
    " ON recovery.execution_id=recovered.execution_id"
    " AND recovery.attempt_id=recovered.attempt_id"
    " WHERE recovered.execution_id=execution.execution_id"
    " AND recovered.attempt_number=1 AND recovered.status='reconciled'"
    " AND recovered.finished_at IS NOT NULL"
    " AND recovery.kind='absence_confirmed')))"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_receipts receipt"
    " WHERE receipt.handoff_id=handoff.handoff_id)"
)
_CURRENT = text(
    "SELECT 1 FROM release_publication_executions execution"
    " JOIN release_publication_handoffs handoff"
    " ON handoff.handoff_id=execution.handoff_id"
    " JOIN release_publication_current_channels current_channel"
    " ON current_channel.channel_id=handoff.channel_id"
    " AND current_channel.revision_id=handoff.channel_revision_id"
    " JOIN release_publication_channel_revisions channel"
    " ON channel.revision_id=current_channel.revision_id"
    " AND channel.channel_id=current_channel.channel_id"
    " AND channel.status='active'"
    " JOIN release_publication_revision_publishers publisher"
    " ON publisher.revision_id=current_channel.revision_id"
    " AND publisher.channel_id=current_channel.channel_id"
    " AND publisher.authority_id=handoff.publisher_authority_id"
    " AND publisher.status='active'"
    " JOIN release_registry_current_set current_registry"
    " ON current_registry.singleton_key=1"
    " JOIN release_registry_set_revisions registry_revision"
    " ON registry_revision.revision_id=current_registry.revision_id"
    " AND registry_revision.policy_status='active'"
    " JOIN release_registry_revision_signers signer"
    " ON signer.revision_id=current_registry.revision_id"
    " AND signer.authority_id=handoff.signer_authority_id"
    " AND signer.status='active'"
    " JOIN release_registry_revision_keys signing_key"
    " ON signing_key.revision_id=current_registry.revision_id"
    " AND signing_key.key_id=handoff.key_id"
    " AND signing_key.signer_authority_id=handoff.signer_authority_id"
    " AND signing_key.status='active'"
    " WHERE execution.execution_id=:execution"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_reassessments reassessment"
    " WHERE reassessment.handoff_id=handoff.handoff_id"
    " AND reassessment.status='pending')"
)


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleasePublicationReconciliationUnavailable
    try:
        return bytes(value).decode("utf-8")
    except UnicodeError:
        raise ReleasePublicationReconciliationUnavailable from None


class DatabaseReleasePublicationUnknownOutcomeReconciliation:
    """Inspect an unknown external effect exactly once without mutation."""

    __slots__ = ("_engine", "_inspector")

    def __init__(
        self, engine: Engine, *, target_inspector: ReleasePublicationTargetInspector
    ) -> None:
        self._engine = engine
        self._inspector = target_inspector

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationUnknownOutcomeReconciliation()"

    def reconcile_unknown_outcome(self, execution_id, attempt_id):
        try:
            if (
                type(execution_id) is not ReleasePublicationExecutionId
                or type(attempt_id) is not ReleasePublicationAttemptId
            ):
                raise ReleasePublicationReconciliationUnavailable
            values = {
                "execution": execution_id.value.encode(),
                "attempt": attempt_id.value.encode(),
            }
            with self._engine.connect() as connection:
                row = connection.execute(_UNKNOWN, values).first()
                if row is None:
                    return None
                current_authority = connection.execute(_CURRENT, values).first() is not None
            handoff_id = ReleasePublicationHandoffId(_decode(row.handoff_id))
            target = ReleasePublicationTarget(
                ReleasePublicationChannelId(_decode(row.channel_id)),
                ReleasePublicationChannelPolicyRevisionId(
                    _decode(row.channel_revision_id)
                ),
                row.provider_kind, row.target_name, row.package_name,
                row.package_version,
            )
            observation = self._inspector.inspect_target(target)
            if observation is None:
                return ReconciledReleasePublicationOutcome(
                    execution_id, attempt_id, handoff_id,
                    ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED,
                    target, current_authority,
                )
            if type(observation) is not ReleasePublicationTargetObservation:
                raise ReleasePublicationReconciliationUnavailable
            exact = (
                observation.visible is True
                and observation.package_name == target.package_name
                and observation.package_version == target.package_version
                and observation.wheel_sha256 == row.wheel_sha256
            )
            kind = (
                ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED
                if exact else ReleasePublicationReconciliationKind.CONFLICT
            )
            return ReconciledReleasePublicationOutcome(
                execution_id, attempt_id, handoff_id, kind, target,
                current_authority, observation,
            )
        except ReleasePublicationReconciliationUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationReconciliationUnavailable
