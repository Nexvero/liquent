"""Commit write-start before one immutable provider create."""

from __future__ import annotations

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.ports import (
    ReleasePublicationImmutableCreator,
    ReleasePublicationTargetInspection,
)
from liquent_platform.identity.release_publication import (
    InspectedReleasePublicationTarget,
    ReleasePublicationAttemptId,
    ReleasePublicationCreateAcknowledgement,
    ReleasePublicationExecutionId,
    ReleasePublicationHandoffId,
    ReleasePublicationTargetDecisionKind,
    ReleasePublicationWritePendingReconciliation,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationCreateUnavailable,
    ReleasePublicationTargetInspectionUnavailable,
)


_LOCK = text(
    "LOCK TABLE release_registry_current_set,release_registry_set_revisions,"
    " release_registry_revision_signers,release_registry_revision_keys,"
    " release_publication_channel_revisions,release_publication_current_channels,"
    " release_publication_revision_publishers,release_publication_handoffs,"
    " release_publication_receipts,release_publication_reassessments,"
    " release_publication_executions,release_publication_execution_attempts"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_STATE = text(
    "SELECT execution.handoff_id,execution.status AS execution_status,"
    " attempt.status AS attempt_status,attempt.attempt_number,attempt.finished_at"
    " FROM release_publication_executions execution"
    " JOIN release_publication_execution_attempts attempt"
    " ON attempt.execution_id=execution.execution_id"
    " WHERE execution.execution_id=:execution AND attempt.attempt_id=:attempt"
)
_CURRENT = text(
    "SELECT handoff.handoff_id"
    " FROM release_publication_executions execution"
    " JOIN release_publication_execution_attempts attempt"
    " ON attempt.execution_id=execution.execution_id"
    " JOIN release_publication_handoffs handoff"
    " ON handoff.handoff_id=execution.handoff_id"
    " JOIN release_publication_current_channels current_channel"
    " ON current_channel.channel_id=handoff.channel_id"
    " AND current_channel.revision_id=handoff.channel_revision_id"
    " JOIN release_publication_channel_revisions channel"
    " ON channel.revision_id=current_channel.revision_id"
    " AND channel.channel_id=current_channel.channel_id"
    " AND channel.status='active' AND channel.artifact_class='operational_bundle'"
    " AND channel.provider_kind=:provider AND channel.target_name=:target"
    " AND channel.package_name=:package AND handoff.package_version=:version"
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
    " WHERE execution.execution_id=:execution AND attempt.attempt_id=:attempt"
    " AND execution.handoff_id=:handoff"
    " AND execution.bundle_sha256=:bundle AND execution.signature_sha256=:signature"
    " AND handoff.wheel_sha256=:wheel AND handoff.checksums_sha256=:checksums"
    " AND handoff.promotion_evidence_sha256=:evidence"
    " AND execution.status='prepared' AND attempt.status='prepared'"
    " AND attempt.attempt_number=1 AND attempt.finished_at IS NULL"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_receipts receipt"
    " WHERE receipt.handoff_id=handoff.handoff_id)"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_reassessments reassessment"
    " WHERE reassessment.handoff_id=handoff.handoff_id"
    " AND reassessment.status='pending')"
)


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleasePublicationCreateUnavailable
    try:
        return bytes(value).decode("utf-8")
    except UnicodeError:
        raise ReleasePublicationCreateUnavailable from None


class DatabaseReleasePublicationImmutableCreate:
    """Perform at most one immutable create after a committed write-start."""

    __slots__ = ("_engine", "_inspection", "_creator")

    def __init__(
        self,
        engine: Engine,
        *,
        target_inspection: ReleasePublicationTargetInspection,
        immutable_creator: ReleasePublicationImmutableCreator,
    ) -> None:
        self._engine = engine
        self._inspection = target_inspection
        self._creator = immutable_creator

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationImmutableCreate()"

    def create_publication(self, execution_id, attempt_id):
        try:
            if (
                type(execution_id) is not ReleasePublicationExecutionId
                or type(attempt_id) is not ReleasePublicationAttemptId
            ):
                raise ReleasePublicationCreateUnavailable
            existing = self._existing(execution_id, attempt_id)
            if existing is not None:
                return existing
            inspected = self._inspection.inspect_publication_target(
                execution_id, attempt_id
            )
            if inspected is None:
                return None
            if type(inspected) is not InspectedReleasePublicationTarget:
                raise ReleasePublicationCreateUnavailable
            if inspected.kind is not ReleasePublicationTargetDecisionKind.CREATE_ALLOWED:
                return None
            handoff_id = self._start(execution_id, attempt_id, inspected)
            if handoff_id is None:
                return self._existing(execution_id, attempt_id)
            acknowledgement = None
            provider_error = False
            try:
                acknowledgement = self._creator.create_immutable(
                    inspected.target, inspected.artifacts, execution_id
                )
                if type(acknowledgement) is not ReleasePublicationCreateAcknowledgement:
                    provider_error = True
            except Exception:
                provider_error = True
            self._mark_unknown(execution_id, attempt_id)
            if provider_error:
                raise ReleasePublicationCreateUnavailable
            return ReleasePublicationWritePendingReconciliation(
                execution_id, attempt_id, handoff_id, acknowledgement
            )
        except ReleasePublicationCreateUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except ReleasePublicationTargetInspectionUnavailable:
            pass
        except Exception:
            pass
        raise ReleasePublicationCreateUnavailable

    def _existing(self, execution_id, attempt_id):
        with self._engine.connect() as connection:
            row = connection.execute(_STATE, {
                "execution": execution_id.value.encode(),
                "attempt": attempt_id.value.encode(),
            }).first()
        if row is None:
            return None
        handoff_id = ReleasePublicationHandoffId(_decode(row.handoff_id))
        if row.attempt_number != 1 or row.finished_at is not None:
            return None
        state = (row.execution_status, row.attempt_status)
        if state == ("prepared", "prepared"):
            return None
        if state == ("prepared", "write_started"):
            self._mark_unknown(execution_id, attempt_id)
            return ReleasePublicationWritePendingReconciliation(
                execution_id, attempt_id, handoff_id
            )
        if state == ("outcome_unknown", "outcome_unknown"):
            return ReleasePublicationWritePendingReconciliation(
                execution_id, attempt_id, handoff_id
            )
        if state[0] in {"published", "published_reassessment_required"}:
            return None
        raise ReleasePublicationCreateUnavailable

    def _start(self, execution_id, attempt_id, inspected):
        values = {
            "execution": execution_id.value.encode(),
            "attempt": attempt_id.value.encode(),
            "handoff": inspected.artifacts.handoff_id.value.encode(),
            "provider": inspected.target.provider_kind,
            "target": inspected.target.target_name,
            "package": inspected.target.package_name,
            "version": inspected.target.package_version,
            "bundle": inspected.artifacts.bundle_sha256,
            "wheel": inspected.artifacts.wheel_sha256,
            "checksums": inspected.artifacts.checksums_sha256,
            "signature": inspected.artifacts.signature_sha256,
            "evidence": inspected.artifacts.promotion_evidence_sha256,
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
            elif transaction.dialect.name != "sqlite":
                raise ReleasePublicationCreateUnavailable
            current = transaction.execute(_CURRENT, values).first()
            if current is None:
                return None
            updated = transaction.execute(text(
                "UPDATE release_publication_execution_attempts SET status='write_started'"
                " WHERE attempt_id=:attempt AND status='prepared'"
            ), values)
            if updated.rowcount != 1:
                return None
            return ReleasePublicationHandoffId(_decode(current.handoff_id))

    def _mark_unknown(self, execution_id, attempt_id):
        values = {
            "execution": execution_id.value.encode(),
            "attempt": attempt_id.value.encode(),
        }
        with self._engine.begin() as transaction:
            attempt = transaction.execute(text(
                "UPDATE release_publication_execution_attempts"
                " SET status='outcome_unknown'"
                " WHERE attempt_id=:attempt AND execution_id=:execution"
                " AND status='write_started'"
            ), values)
            transaction.execute(text(
                "UPDATE release_publication_executions SET status='outcome_unknown'"
                " WHERE execution_id=:execution AND status='prepared'"
            ), values)
            if attempt.rowcount != 1:
                row = transaction.execute(_STATE, values).first()
                if row is None or row.attempt_status != "outcome_unknown":
                    raise ReleasePublicationCreateUnavailable
