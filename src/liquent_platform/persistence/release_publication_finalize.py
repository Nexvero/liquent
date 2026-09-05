"""Atomic persistent finalization of one confirmed external publication."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.ports import (
    ReleasePublicationUnknownOutcomeReconciliation,
)
from liquent_platform.identity.release_publication import (
    FinalizedReleasePublication,
    ReconciledReleasePublicationOutcome,
    ReleasePublicationAttemptId,
    ReleasePublicationExecutionId,
    ReleasePublicationFinalStatus,
    ReleasePublicationHandoffId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationReconciliationKind,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationReconciliationFinalizeUnavailable,
    ReleasePublicationReconciliationUnavailable,
)


_LOCK = text(
    "LOCK TABLE release_registry_current_set,release_registry_set_revisions,"
    " release_registry_revision_signers,release_registry_revision_keys,"
    " release_publication_channel_revisions,release_publication_current_channels,"
    " release_publication_revision_publishers,release_publication_handoffs,"
    " release_publication_receipts,release_publication_reassessments,"
    " release_publication_executions,release_publication_execution_attempts,"
    " release_publication_receipt_reconciliations,"
    " release_publication_execution_reassessments IN SHARE ROW EXCLUSIVE MODE"
)
_EXISTING = text(
    "SELECT receipt.receipt_id,reconciliation.status,reassessment.reassessment_id,"
    " execution.handoff_id,attempt.attempt_id"
    " FROM release_publication_receipt_reconciliations reconciliation"
    " JOIN release_publication_receipts receipt"
    " ON receipt.receipt_id=reconciliation.receipt_id"
    " JOIN release_publication_executions execution"
    " ON execution.execution_id=reconciliation.execution_id"
    " JOIN release_publication_execution_attempts attempt"
    " ON attempt.attempt_id=reconciliation.attempt_id"
    " LEFT JOIN release_publication_execution_reassessments reassessment"
    " ON reassessment.execution_id=execution.execution_id"
    " WHERE reconciliation.execution_id=:execution"
    " AND reconciliation.attempt_id=:attempt"
)
_UNKNOWN = text(
    "SELECT handoff.handoff_id,handoff.channel_id,handoff.channel_revision_id,"
    " channel.provider_kind,channel.target_name,channel.package_name,"
    " handoff.package_version,handoff.bundle_sha256,handoff.wheel_sha256,"
    " attempt.attempt_number,"
    " handoff.signer_authority_id,handoff.key_id"
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
    "SELECT 1 FROM release_publication_current_channels current_channel"
    " JOIN release_publication_channel_revisions channel"
    " ON channel.revision_id=current_channel.revision_id"
    " AND channel.channel_id=current_channel.channel_id"
    " AND channel.status='active'"
    " JOIN release_publication_revision_publishers publisher"
    " ON publisher.revision_id=current_channel.revision_id"
    " AND publisher.channel_id=current_channel.channel_id"
    " AND publisher.authority_id=(SELECT publisher_authority_id"
    " FROM release_publication_handoffs WHERE handoff_id=:handoff)"
    " AND publisher.status='active'"
    " JOIN release_registry_current_set current_registry"
    " ON current_registry.singleton_key=1"
    " JOIN release_registry_set_revisions registry_revision"
    " ON registry_revision.revision_id=current_registry.revision_id"
    " AND registry_revision.policy_status='active'"
    " JOIN release_registry_revision_signers signer"
    " ON signer.revision_id=current_registry.revision_id"
    " AND signer.authority_id=:signer AND signer.status='active'"
    " JOIN release_registry_revision_keys signing_key"
    " ON signing_key.revision_id=current_registry.revision_id"
    " AND signing_key.key_id=:key"
    " AND signing_key.signer_authority_id=:signer"
    " AND signing_key.status='active'"
    " WHERE current_channel.channel_id=:channel"
    " AND current_channel.revision_id=:channel_revision"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_reassessments reassessment"
    " WHERE reassessment.handoff_id=:handoff AND reassessment.status='pending')"
)
_PENDING = text(
    "SELECT reassessment_id FROM release_publication_reassessments"
    " WHERE handoff_id=:handoff AND status='pending' ORDER BY created_at LIMIT 1"
)


def _encode(value: str) -> bytes:
    if type(value) is not str or not value:
        raise ReleasePublicationReconciliationFinalizeUnavailable
    return value.encode("utf-8")


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleasePublicationReconciliationFinalizeUnavailable
    try:
        return bytes(value).decode("utf-8")
    except UnicodeError:
        raise ReleasePublicationReconciliationFinalizeUnavailable from None


class DatabaseReleasePublicationReconciliationFinalizer:
    """Persist a confirmed publication and preserve revocation as reassessment."""

    __slots__ = (
        "_engine", "_reconciliation", "_generate_receipt_id",
        "_generate_reassessment_id", "_clock",
    )

    def __init__(
        self,
        engine: Engine,
        *,
        reconciliation: ReleasePublicationUnknownOutcomeReconciliation,
        generate_receipt_id: Callable[[], ReleasePublicationProviderReceiptId],
        generate_reassessment_id: Callable[[], ReleasePublicationReassessmentId],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._engine = engine
        self._reconciliation = reconciliation
        self._generate_receipt_id = generate_receipt_id
        self._generate_reassessment_id = generate_reassessment_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationReconciliationFinalizer()"

    def finalize_reconciliation(self, execution_id, attempt_id):
        try:
            if (
                type(execution_id) is not ReleasePublicationExecutionId
                or type(attempt_id) is not ReleasePublicationAttemptId
            ):
                raise ReleasePublicationReconciliationFinalizeUnavailable
            existing = self._existing(execution_id, attempt_id)
            if existing is not None:
                return existing
            outcome = self._reconciliation.reconcile_unknown_outcome(
                execution_id, attempt_id
            )
            if outcome is None:
                return None
            if type(outcome) is not ReconciledReleasePublicationOutcome:
                raise ReleasePublicationReconciliationFinalizeUnavailable
            if outcome.kind is not ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED:
                return None
            return self._commit(execution_id, attempt_id, outcome)
        except ReleasePublicationReconciliationFinalizeUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except ReleasePublicationReconciliationUnavailable:
            pass
        except Exception:
            pass
        raise ReleasePublicationReconciliationFinalizeUnavailable

    def existing_finalization(self, execution_id, attempt_id):
        if (
            type(execution_id) is not ReleasePublicationExecutionId
            or type(attempt_id) is not ReleasePublicationAttemptId
        ):
            raise ReleasePublicationReconciliationFinalizeUnavailable
        return self._existing(execution_id, attempt_id)

    def commit_reconciled_outcome(self, execution_id, attempt_id, outcome):
        try:
            existing = self.existing_finalization(execution_id, attempt_id)
            if existing is not None:
                return existing
            if (
                type(outcome) is not ReconciledReleasePublicationOutcome
                or outcome.execution_id != execution_id
                or outcome.attempt_id != attempt_id
                or outcome.kind
                is not ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED
            ):
                return None
            return self._commit(execution_id, attempt_id, outcome)
        except ReleasePublicationReconciliationFinalizeUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationReconciliationFinalizeUnavailable

    def _existing(self, execution_id, attempt_id):
        with self._engine.connect() as connection:
            rows = connection.execute(_EXISTING, {
                "execution": _encode(execution_id.value),
                "attempt": _encode(attempt_id.value),
            }).all()
        if not rows:
            return None
        return self._render_existing(execution_id, rows)

    def _render_existing(self, execution_id, rows):
        if len(rows) != 1:
            raise ReleasePublicationReconciliationFinalizeUnavailable
        row = rows[0]
        status = ReleasePublicationFinalStatus(row.status)
        reassessment = (
            ReleasePublicationReassessmentId(_decode(row.reassessment_id))
            if row.reassessment_id is not None else None
        )
        return FinalizedReleasePublication(
            ReleasePublicationProviderReceiptId(_decode(row.receipt_id)),
            execution_id, ReleasePublicationAttemptId(_decode(row.attempt_id)),
            ReleasePublicationHandoffId(_decode(row.handoff_id)), status,
            reassessment,
        )

    def _commit(self, execution_id, attempt_id, outcome):
        observation = outcome.observation
        if observation is None:
            raise ReleasePublicationReconciliationFinalizeUnavailable
        values = {
            "execution": _encode(execution_id.value),
            "attempt": _encode(attempt_id.value),
            "handoff": _encode(outcome.handoff_id.value),
            "channel": _encode(outcome.target.channel_id.value),
            "channel_revision": _encode(outcome.target.channel_revision_id.value),
            "provider": outcome.target.provider_kind,
            "target": outcome.target.target_name,
            "package": outcome.target.package_name,
            "version": outcome.target.package_version,
            "external": _encode(observation.canonical_artifact_id),
            "provider_revision": _encode(observation.provider_revision),
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
            elif transaction.dialect.name != "sqlite":
                raise ReleasePublicationReconciliationFinalizeUnavailable
            existing = transaction.execute(_EXISTING, values).all()
            if existing:
                return self._render_existing(execution_id, existing)
            row = transaction.execute(_UNKNOWN, values).first()
            if row is None or (
                row.channel_id != values["channel"]
                or row.channel_revision_id != values["channel_revision"]
                or row.provider_kind != values["provider"]
                or row.target_name != values["target"]
                or row.package_name != values["package"]
                or row.package_version != values["version"]
                or row.wheel_sha256 != observation.wheel_sha256
                or observation.visible is not True
            ):
                return None
            values.update({
                "signer": bytes(row.signer_authority_id),
                "key": bytes(row.key_id),
            })
            current = transaction.execute(_CURRENT, values).first() is not None
            pending = transaction.execute(_PENDING, values).first()
            reassessment_id = None
            if not current:
                if pending is not None:
                    reassessment_id = ReleasePublicationReassessmentId(
                        _decode(pending.reassessment_id)
                    )
                else:
                    reassessment_id = self._generate_reassessment_id()
                    if type(reassessment_id) is not ReleasePublicationReassessmentId:
                        raise ReleasePublicationReconciliationFinalizeUnavailable
            receipt_id = self._generate_receipt_id()
            now = self._clock()
            if type(receipt_id) is not ReleasePublicationProviderReceiptId:
                raise ReleasePublicationReconciliationFinalizeUnavailable
            if not isinstance(now, datetime) or now.tzinfo is None:
                raise ReleasePublicationReconciliationFinalizeUnavailable
            now = now.astimezone(timezone.utc)
            status = (
                ReleasePublicationFinalStatus.PUBLISHED
                if current else
                ReleasePublicationFinalStatus.PUBLISHED_REASSESSMENT_REQUIRED
            )
            values.update({
                "receipt": _encode(receipt_id.value), "now": now,
                "status": status.value,
            })
            transaction.execute(text(
                "INSERT INTO release_publication_receipts VALUES "
                "(:receipt,:handoff,:provider_revision,:bundle,:now)"
            ), {**values, "bundle": row.bundle_sha256})
            transaction.execute(text(
                "INSERT INTO release_publication_receipt_reconciliations VALUES "
                "(:receipt,:execution,:attempt,:external,:provider_revision,:now,:status)"
            ), values)
            if reassessment_id is not None:
                values["reassessment"] = _encode(reassessment_id.value)
                if pending is None:
                    transaction.execute(text(
                        "INSERT INTO release_publication_reassessments VALUES "
                        "(:reassessment,:handoff,'reassess','pending',:now)"
                    ), values)
                transaction.execute(text(
                    "INSERT INTO release_publication_execution_reassessments VALUES "
                    "(:execution,:reassessment)"
                ), values)
            transaction.execute(text(
                "UPDATE release_publication_execution_attempts"
                " SET status='reconciled',finished_at=:now WHERE attempt_id=:attempt"
            ), values)
            transaction.execute(text(
                "UPDATE release_publication_executions SET status=:status"
                " WHERE execution_id=:execution"
            ), values)
            return FinalizedReleasePublication(
                receipt_id, execution_id, attempt_id, outcome.handoff_id,
                status, reassessment_id,
            )
