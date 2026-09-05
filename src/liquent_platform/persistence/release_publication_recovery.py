"""Atomic persistent finalization of absence and conflict recovery."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import Engine, text

from liquent_platform.identity.ports import ReleasePublicationUnknownOutcomeReconciliation
from liquent_platform.identity.release_publication import (
    FinalizedReleasePublicationRecovery,
    ReconciledReleasePublicationOutcome,
    ReleasePublicationAttemptId,
    ReleasePublicationExecutionId,
    ReleasePublicationHandoffId,
    ReleasePublicationReassessmentId,
    ReleasePublicationReconciliationKind,
    ReleasePublicationRecoveryId,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationReconciliationUnavailable,
    ReleasePublicationRecoveryFinalizeUnavailable,
)


_LOCK = text(
    "LOCK TABLE release_registry_current_set,release_registry_set_revisions,"
    " release_registry_revision_signers,release_registry_revision_keys,"
    " release_publication_channel_revisions,release_publication_current_channels,"
    " release_publication_revision_publishers,release_publication_handoffs,"
    " release_publication_receipts,release_publication_reassessments,"
    " release_publication_executions,release_publication_execution_attempts,"
    " release_publication_execution_reassessments,"
    " release_publication_recovery_decisions IN SHARE ROW EXCLUSIVE MODE"
)
_EXISTING = text(
    "SELECT recovery.recovery_id,recovery.kind,recovery.current_authority,"
    " recovery.reassessment_id,execution.handoff_id,recovery.attempt_id,"
    " attempt.attempt_number"
    " FROM release_publication_recovery_decisions recovery"
    " JOIN release_publication_executions execution"
    " ON execution.execution_id=recovery.execution_id"
    " JOIN release_publication_execution_attempts attempt"
    " ON attempt.attempt_id=recovery.attempt_id"
    " WHERE recovery.execution_id=:execution AND recovery.attempt_id=:attempt"
)
_UNKNOWN = text(
    "SELECT handoff.handoff_id,handoff.channel_id,handoff.channel_revision_id,"
    " channel.provider_kind,channel.target_name,channel.package_name,"
    " handoff.package_version,handoff.wheel_sha256,attempt.attempt_number,"
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
    " AND execution.status='outcome_unknown' AND attempt.status='outcome_unknown'"
    " AND attempt.finished_at IS NULL AND (attempt.attempt_number=1 OR"
    " (attempt.attempt_number=2 AND EXISTS"
    " (SELECT 1 FROM release_publication_execution_attempts recovered"
    " JOIN release_publication_recovery_decisions prior_recovery"
    " ON prior_recovery.execution_id=recovered.execution_id"
    " AND prior_recovery.attempt_id=recovered.attempt_id"
    " WHERE recovered.execution_id=execution.execution_id"
    " AND recovered.attempt_number=1 AND recovered.status='reconciled'"
    " AND recovered.finished_at IS NOT NULL"
    " AND prior_recovery.kind='absence_confirmed')))"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_receipts receipt"
    " WHERE receipt.handoff_id=handoff.handoff_id)"
)
_CURRENT = text(
    "SELECT 1 FROM release_publication_current_channels current_channel"
    " JOIN release_publication_channel_revisions channel"
    " ON channel.revision_id=current_channel.revision_id"
    " AND channel.channel_id=current_channel.channel_id AND channel.status='active'"
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
    " AND signing_key.key_id=:key AND signing_key.signer_authority_id=:signer"
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
        raise ReleasePublicationRecoveryFinalizeUnavailable
    return value.encode("utf-8")


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleasePublicationRecoveryFinalizeUnavailable
    try:
        return bytes(value).decode("utf-8")
    except UnicodeError:
        raise ReleasePublicationRecoveryFinalizeUnavailable from None


class DatabaseReleasePublicationRecoveryFinalizer:
    """Close one non-success outcome without permitting an immediate retry."""

    __slots__ = (
        "_engine", "_reconciliation", "_generate_recovery_id",
        "_generate_reassessment_id", "_clock",
    )

    def __init__(
        self,
        engine: Engine,
        *,
        reconciliation: ReleasePublicationUnknownOutcomeReconciliation,
        generate_recovery_id: Callable[[], ReleasePublicationRecoveryId],
        generate_reassessment_id: Callable[[], ReleasePublicationReassessmentId],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._engine = engine
        self._reconciliation = reconciliation
        self._generate_recovery_id = generate_recovery_id
        self._generate_reassessment_id = generate_reassessment_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationRecoveryFinalizer()"

    def finalize_recovery(self, execution_id, attempt_id):
        try:
            if (
                type(execution_id) is not ReleasePublicationExecutionId
                or type(attempt_id) is not ReleasePublicationAttemptId
            ):
                raise ReleasePublicationRecoveryFinalizeUnavailable
            existing = self._existing(execution_id, attempt_id)
            if existing is not None:
                return existing
            outcome = self._reconciliation.reconcile_unknown_outcome(
                execution_id, attempt_id
            )
            if outcome is None:
                return None
            if type(outcome) is not ReconciledReleasePublicationOutcome:
                raise ReleasePublicationRecoveryFinalizeUnavailable
            if outcome.kind is ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED:
                return None
            return self._commit(execution_id, attempt_id, outcome)
        except ReleasePublicationRecoveryFinalizeUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except ReleasePublicationReconciliationUnavailable:
            pass
        except Exception:
            pass
        raise ReleasePublicationRecoveryFinalizeUnavailable

    def existing_finalization(self, execution_id, attempt_id):
        if (
            type(execution_id) is not ReleasePublicationExecutionId
            or type(attempt_id) is not ReleasePublicationAttemptId
        ):
            raise ReleasePublicationRecoveryFinalizeUnavailable
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
                is ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED
            ):
                return None
            return self._commit(execution_id, attempt_id, outcome)
        except ReleasePublicationRecoveryFinalizeUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationRecoveryFinalizeUnavailable

    def _existing(self, execution_id, attempt_id):
        with self._engine.connect() as connection:
            rows = connection.execute(_EXISTING, {
                "execution": _encode(execution_id.value),
                "attempt": _encode(attempt_id.value),
            }).all()
        if not rows:
            return None
        return self._render(execution_id, rows)

    def _render(self, execution_id, rows):
        if len(rows) != 1:
            raise ReleasePublicationRecoveryFinalizeUnavailable
        row = rows[0]
        if row.current_authority not in {True, False, 0, 1}:
            raise ReleasePublicationRecoveryFinalizeUnavailable
        kind = ReleasePublicationReconciliationKind(row.kind)
        reassessment = (
            ReleasePublicationReassessmentId(_decode(row.reassessment_id))
            if row.reassessment_id is not None else None
        )
        return FinalizedReleasePublicationRecovery(
            ReleasePublicationRecoveryId(_decode(row.recovery_id)), execution_id,
            ReleasePublicationAttemptId(_decode(row.attempt_id)),
            ReleasePublicationHandoffId(_decode(row.handoff_id)), kind,
            kind is ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED
            and row.attempt_number == 1 and bool(row.current_authority),
            reassessment,
        )

    def _commit(self, execution_id, attempt_id, outcome):
        observation = outcome.observation
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
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
            elif transaction.dialect.name != "sqlite":
                raise ReleasePublicationRecoveryFinalizeUnavailable
            existing = transaction.execute(_EXISTING, values).all()
            if existing:
                return self._render(execution_id, existing)
            row = transaction.execute(_UNKNOWN, values).first()
            if row is None or (
                row.channel_id != values["channel"]
                or row.channel_revision_id != values["channel_revision"]
                or row.provider_kind != values["provider"]
                or row.target_name != values["target"]
                or row.package_name != values["package"]
                or row.package_version != values["version"]
            ):
                return None
            if row.attempt_number not in {1, 2}:
                raise ReleasePublicationRecoveryFinalizeUnavailable
            absence = outcome.kind is ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED
            conflict = outcome.kind is ReleasePublicationReconciliationKind.CONFLICT
            if absence != (observation is None) or not (absence or conflict):
                raise ReleasePublicationRecoveryFinalizeUnavailable
            if conflict and observation is not None:
                exact = (
                    observation.visible is True
                    and observation.package_name == row.package_name
                    and observation.package_version == row.package_version
                    and observation.wheel_sha256 == row.wheel_sha256
                )
                if exact:
                    return None
            values.update({
                "signer": bytes(row.signer_authority_id),
                "key": bytes(row.key_id),
            })
            current = transaction.execute(_CURRENT, values).first() is not None
            recovery_id = self._generate_recovery_id()
            now = self._clock()
            if type(recovery_id) is not ReleasePublicationRecoveryId:
                raise ReleasePublicationRecoveryFinalizeUnavailable
            if not isinstance(now, datetime) or now.tzinfo is None:
                raise ReleasePublicationRecoveryFinalizeUnavailable
            values.update({
                "recovery": _encode(recovery_id.value),
                "kind": outcome.kind.value,
                "current": current,
                "now": now.astimezone(timezone.utc),
                "external": None,
                "provider_revision": None,
                "reassessment": None,
            })
            reassessment_id = None
            if conflict:
                pending = transaction.execute(_PENDING, values).first()
                if pending is not None:
                    reassessment_id = ReleasePublicationReassessmentId(
                        _decode(pending.reassessment_id)
                    )
                else:
                    reassessment_id = self._generate_reassessment_id()
                    if type(reassessment_id) is not ReleasePublicationReassessmentId:
                        raise ReleasePublicationRecoveryFinalizeUnavailable
                    values["reassessment"] = _encode(reassessment_id.value)
                    transaction.execute(text(
                        "INSERT INTO release_publication_reassessments VALUES "
                        "(:reassessment,:handoff,'reassess','pending',:now)"
                    ), values)
                values.update({
                    "reassessment": _encode(reassessment_id.value),
                    "external": _encode(observation.canonical_artifact_id),
                    "provider_revision": _encode(observation.provider_revision),
                })
                transaction.execute(text(
                    "INSERT INTO release_publication_execution_reassessments "
                    "SELECT :execution,:reassessment WHERE NOT EXISTS (SELECT 1 FROM "
                    "release_publication_execution_reassessments WHERE "
                    "execution_id=:execution AND reassessment_id=:reassessment)"
                ), values)
            transaction.execute(text(
                "INSERT INTO release_publication_recovery_decisions VALUES "
                "(:recovery,:execution,:attempt,:kind,:current,:external,"
                ":provider_revision,:reassessment,:now)"
            ), values)
            transaction.execute(text(
                "UPDATE release_publication_execution_attempts"
                " SET status='reconciled',finished_at=:now WHERE attempt_id=:attempt"
            ), values)
            if absence and row.attempt_number == 1:
                transaction.execute(text(
                    "UPDATE release_publication_executions SET status='prepared'"
                    " WHERE execution_id=:execution"
                ), values)
            elif row.attempt_number == 2:
                values["terminal_status"] = (
                    "not_published" if absence else "publication_conflict"
                )
                transaction.execute(text(
                    "UPDATE release_publication_executions SET status=:terminal_status"
                    " WHERE execution_id=:execution"
                ), values)
            return FinalizedReleasePublicationRecovery(
                recovery_id, execution_id, attempt_id, outcome.handoff_id,
                outcome.kind, absence and row.attempt_number == 1 and current,
                reassessment_id,
            )
