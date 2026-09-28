"""Fresh attempt-2 preflight after one confirmed-absence recovery."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.ports import (
    ReleasePublicationArtifactIntegrityCheck,
    ReleasePublicationTargetInspector,
)
from liquent_platform.identity.release_publication import (
    PreparedReleasePublicationAttempt,
    ReleasePublicationAttemptId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationHandoffId,
    ReleasePublicationTarget,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationArtifactIntegrityUnavailable,
    ReleasePublicationRetryAttemptUnavailable,
)


_LOCK = text(
    "LOCK TABLE release_registry_current_set,release_registry_set_revisions,"
    " release_registry_revision_signers,release_registry_revision_keys,"
    " release_publication_channel_revisions,release_publication_current_channels,"
    " release_publication_revision_publishers,release_publication_handoffs,"
    " release_publication_receipts,release_publication_reassessments,"
    " release_publication_executions,release_publication_execution_attempts,"
    " release_publication_recovery_decisions IN SHARE ROW EXCLUSIVE MODE"
)
_EXISTING = text(
    "SELECT attempt.attempt_id,execution.handoff_id,attempt.attempt_number,"
    " attempt.status,attempt.finished_at"
    " FROM release_publication_execution_attempts attempt"
    " JOIN release_publication_executions execution"
    " ON execution.execution_id=attempt.execution_id"
    " WHERE attempt.execution_id=:execution AND attempt.attempt_number=2"
)
_ELIGIBLE = text(
    "SELECT handoff.handoff_id,handoff.channel_id,handoff.channel_revision_id,"
    " channel.provider_kind,channel.target_name,channel.package_name,"
    " handoff.package_version,handoff.bundle_sha256,handoff.wheel_sha256,"
    " handoff.checksums_sha256,handoff.signature_sha256,"
    " handoff.promotion_evidence_sha256"
    " FROM release_publication_executions execution"
    " JOIN release_publication_execution_attempts recovered"
    " ON recovered.execution_id=execution.execution_id"
    " JOIN release_publication_recovery_decisions recovery"
    " ON recovery.execution_id=execution.execution_id"
    " AND recovery.attempt_id=recovered.attempt_id"
    " AND recovery.kind='absence_confirmed' AND recovery.current_authority IS TRUE"
    " JOIN release_publication_handoffs handoff"
    " ON handoff.handoff_id=execution.handoff_id"
    " JOIN release_publication_current_channels current_channel"
    " ON current_channel.channel_id=handoff.channel_id"
    " AND current_channel.revision_id=handoff.channel_revision_id"
    " JOIN release_publication_channel_revisions channel"
    " ON channel.revision_id=current_channel.revision_id"
    " AND channel.channel_id=current_channel.channel_id"
    " AND channel.status='active' AND channel.artifact_class='operational_bundle'"
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
    " AND signer.authority_id=handoff.signer_authority_id AND signer.status='active'"
    " JOIN release_registry_revision_keys signing_key"
    " ON signing_key.revision_id=current_registry.revision_id"
    " AND signing_key.key_id=handoff.key_id"
    " AND signing_key.signer_authority_id=handoff.signer_authority_id"
    " AND signing_key.status='active'"
    " WHERE execution.execution_id=:execution"
    " AND recovered.attempt_id=:recovered AND recovered.attempt_number=1"
    " AND recovered.status='reconciled' AND recovered.finished_at IS NOT NULL"
    " AND execution.status='prepared'"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_receipts receipt"
    " WHERE receipt.handoff_id=handoff.handoff_id)"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_reassessments reassessment"
    " WHERE reassessment.handoff_id=handoff.handoff_id"
    " AND reassessment.status='pending')"
)


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleasePublicationRetryAttemptUnavailable
    try:
        return bytes(value).decode("utf-8")
    except UnicodeError:
        raise ReleasePublicationRetryAttemptUnavailable from None


class DatabaseReleasePublicationRetryAttemptPreflight:
    """Prepare attempt 2 after fresh integrity, authority, and absence checks."""

    __slots__ = ("_engine", "_integrity", "_inspector", "_generate_attempt_id", "_clock")

    def __init__(
        self,
        engine: Engine,
        *,
        artifact_integrity: ReleasePublicationArtifactIntegrityCheck,
        target_inspector: ReleasePublicationTargetInspector,
        generate_attempt_id: Callable[[], ReleasePublicationAttemptId],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._engine = engine
        self._integrity = artifact_integrity
        self._inspector = target_inspector
        self._generate_attempt_id = generate_attempt_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationRetryAttemptPreflight()"

    def prepare_retry_attempt(self, execution_id, recovered_attempt_id):
        try:
            if (
                type(execution_id) is not ReleasePublicationExecutionId
                or type(recovered_attempt_id) is not ReleasePublicationAttemptId
            ):
                raise ReleasePublicationRetryAttemptUnavailable
            existing = self._existing(execution_id)
            if existing is not None:
                return existing
            artifacts = self._integrity.verify_artifacts(
                execution_id, recovered_attempt_id
            )
            if artifacts is None:
                return None
            values = {
                "execution": execution_id.value.encode(),
                "recovered": recovered_attempt_id.value.encode(),
            }
            with self._engine.connect() as connection:
                row = connection.execute(_ELIGIBLE, values).first()
            if row is None or (
                _decode(row.handoff_id) != artifacts.handoff_id.value
                or row.package_version != artifacts.package_version
                or row.bundle_sha256 != artifacts.bundle_sha256
                or row.wheel_sha256 != artifacts.wheel_sha256
                or row.checksums_sha256 != artifacts.checksums_sha256
                or row.signature_sha256 != artifacts.signature_sha256
                or row.promotion_evidence_sha256 != artifacts.promotion_evidence_sha256
            ):
                return None
            target = self._target(row)
            if self._inspector.inspect_target(target) is not None:
                return None
            return self._commit(execution_id, recovered_attempt_id, artifacts, target)
        except ReleasePublicationRetryAttemptUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except ReleasePublicationArtifactIntegrityUnavailable:
            pass
        except Exception:
            pass
        raise ReleasePublicationRetryAttemptUnavailable

    def _existing(self, execution_id):
        with self._engine.connect() as connection:
            rows = connection.execute(_EXISTING, {
                "execution": execution_id.value.encode()
            }).all()
        if not rows:
            return None
        return self._render_existing(execution_id, rows)

    def _render_existing(self, execution_id, rows):
        if len(rows) != 1:
            raise ReleasePublicationRetryAttemptUnavailable
        row = rows[0]
        if row.attempt_number != 2 or row.status != "prepared" or row.finished_at is not None:
            return None
        return PreparedReleasePublicationAttempt(
            execution_id, ReleasePublicationAttemptId(_decode(row.attempt_id)),
            ReleasePublicationHandoffId(_decode(row.handoff_id)), 2,
        )

    def _target(self, row):
        return ReleasePublicationTarget(
            ReleasePublicationChannelId(_decode(row.channel_id)),
            ReleasePublicationChannelPolicyRevisionId(_decode(row.channel_revision_id)),
            row.provider_kind, row.target_name, row.package_name, row.package_version,
        )

    def _commit(self, execution_id, recovered_attempt_id, artifacts, target):
        values = {
            "execution": execution_id.value.encode(),
            "recovered": recovered_attempt_id.value.encode(),
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
            elif transaction.dialect.name != "sqlite":
                raise ReleasePublicationRetryAttemptUnavailable
            existing = transaction.execute(_EXISTING, values).all()
            if existing:
                return self._render_existing(execution_id, existing)
            row = transaction.execute(_ELIGIBLE, values).first()
            if row is None or (
                _decode(row.handoff_id) != artifacts.handoff_id.value
                or row.provider_kind != target.provider_kind
                or row.target_name != target.target_name
                or row.package_name != target.package_name
                or row.package_version != target.package_version
            ):
                return None
            attempt_id = self._generate_attempt_id()
            now = self._clock()
            if type(attempt_id) is not ReleasePublicationAttemptId:
                raise ReleasePublicationRetryAttemptUnavailable
            if not isinstance(now, datetime) or now.tzinfo is None:
                raise ReleasePublicationRetryAttemptUnavailable
            values.update({
                "attempt": attempt_id.value.encode(),
                "now": now.astimezone(timezone.utc),
            })
            transaction.execute(text(
                "INSERT INTO release_publication_execution_attempts VALUES "
                "(:attempt,:execution,2,'prepared',:now,NULL)"
            ), values)
            return PreparedReleasePublicationAttempt(
                execution_id, attempt_id, artifacts.handoff_id, 2,
            )
