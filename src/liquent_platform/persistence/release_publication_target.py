"""Read-only publication-target inspection after artifact verification."""

from __future__ import annotations

from sqlalchemy import Engine, text

from liquent_platform.identity.ports import (
    ReleasePublicationArtifactIntegrityCheck,
    ReleasePublicationTargetInspector,
)
from liquent_platform.identity.release_publication import (
    InspectedReleasePublicationTarget,
    ReleasePublicationAttemptId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationTarget,
    ReleasePublicationTargetDecisionKind,
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationArtifactIntegrityUnavailable,
    ReleasePublicationTargetInspectionUnavailable,
)


_TARGET = text(
    "SELECT handoff.channel_id,handoff.channel_revision_id,"
    " channel.provider_kind,channel.target_name,channel.package_name,"
    " handoff.package_version"
    " FROM release_publication_executions execution"
    " JOIN release_publication_execution_attempts attempt"
    " ON attempt.execution_id=execution.execution_id"
    " JOIN release_publication_handoffs handoff"
    " ON handoff.handoff_id=execution.handoff_id"
    " JOIN release_publication_current_channels current"
    " ON current.channel_id=handoff.channel_id"
    " AND current.revision_id=handoff.channel_revision_id"
    " JOIN release_publication_channel_revisions channel"
    " ON channel.revision_id=current.revision_id"
    " AND channel.channel_id=current.channel_id"
    " AND channel.status='active'"
    " AND channel.artifact_class='operational_bundle'"
    " JOIN release_publication_revision_publishers publisher"
    " ON publisher.revision_id=current.revision_id"
    " AND publisher.channel_id=current.channel_id"
    " AND publisher.authority_id=handoff.publisher_authority_id"
    " AND publisher.status='active'"
    " WHERE execution.execution_id=:execution AND attempt.attempt_id=:attempt"
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
        raise ReleasePublicationTargetInspectionUnavailable
    try:
        return bytes(value).decode("utf-8")
    except UnicodeError:
        raise ReleasePublicationTargetInspectionUnavailable from None


class DatabaseReleasePublicationTargetInspection:
    """Resolve the current target and inspect it exactly once, read-only."""

    __slots__ = ("_engine", "_integrity", "_inspector")

    def __init__(
        self,
        engine: Engine,
        *,
        artifact_integrity: ReleasePublicationArtifactIntegrityCheck,
        target_inspector: ReleasePublicationTargetInspector,
    ) -> None:
        self._engine = engine
        self._integrity = artifact_integrity
        self._inspector = target_inspector

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationTargetInspection()"

    def inspect_publication_target(self, execution_id, attempt_id):
        try:
            if (
                type(execution_id) is not ReleasePublicationExecutionId
                or type(attempt_id) is not ReleasePublicationAttemptId
            ):
                raise ReleasePublicationTargetInspectionUnavailable
            artifacts = self._integrity.verify_artifacts(execution_id, attempt_id)
            if artifacts is None:
                return None
            with self._engine.connect() as connection:
                row = connection.execute(_TARGET, {
                    "execution": execution_id.value.encode(),
                    "attempt": attempt_id.value.encode(),
                }).first()
            if row is None:
                return None
            target = ReleasePublicationTarget(
                ReleasePublicationChannelId(_decode(row.channel_id)),
                ReleasePublicationChannelPolicyRevisionId(
                    _decode(row.channel_revision_id)
                ),
                row.provider_kind, row.target_name, row.package_name,
                row.package_version,
            )
            if target.package_name != "liquent" or target.package_version != artifacts.package_version:
                raise ReleasePublicationTargetInspectionUnavailable
            observation = self._inspector.inspect_target(target)
            if observation is None:
                return InspectedReleasePublicationTarget(
                    ReleasePublicationTargetDecisionKind.CREATE_ALLOWED,
                    target, artifacts,
                )
            if type(observation) is not ReleasePublicationTargetObservation:
                raise ReleasePublicationTargetInspectionUnavailable
            exact = (
                observation.visible is True
                and observation.package_name == target.package_name
                and observation.package_version == target.package_version
                and observation.wheel_sha256 == artifacts.wheel_sha256
            )
            kind = (
                ReleasePublicationTargetDecisionKind.RECONCILIATION_REQUIRED
                if exact else ReleasePublicationTargetDecisionKind.CONFLICT
            )
            return InspectedReleasePublicationTarget(
                kind, target, artifacts, observation,
            )
        except ReleasePublicationTargetInspectionUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except ReleasePublicationArtifactIntegrityUnavailable:
            pass
        except Exception:
            pass
        raise ReleasePublicationTargetInspectionUnavailable
