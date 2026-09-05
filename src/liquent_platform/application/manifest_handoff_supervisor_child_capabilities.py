"""Profile-closed local capabilities for one supervisor child process."""

from datetime import datetime, timezone
from pathlib import Path

from liquent_platform.capabilities.private_manifest_handoff import (
    ManifestHandoffUnavailable,
    ManifestHandoffUnknown,
)
from liquent_platform.capabilities.private_manifest_handoff_reconcile import (
    ManifestReconciliationUnavailable,
)
from liquent_platform.identity.manifest_handoff import ManifestHandoffFacts
from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
    ManifestHandoffRecoveryProcessKind,
    ManifestHandoffWriterProcessKind,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_executor import (
    ExecuteManifestHandoffRecoveryCapability,
    ExecuteManifestHandoffWriterCapability,
    ExecutedManifestHandoffRecoveryCapability,
    ExecutedManifestHandoffWriterCapability,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class LocalManifestHandoffSupervisorChildCapabilityExecutor:
    """Execute one fixed writer or read-only recovery primitive."""

    __slots__ = ("_clock", "_reconciler", "_source", "_target", "_writer")

    def __init__(self, *, source_root: Path, target_root: Path,
                 writer, reconciler, clock) -> None:
        if (not isinstance(source_root, Path) or not source_root.is_absolute()
                or not isinstance(target_root, Path) or not target_root.is_absolute()
                or source_root == target_root or not callable(writer)
                or not callable(reconciler) or not callable(clock)):
            raise ManifestHandoffRegistryUnavailable
        self._source, self._target = source_root, target_root
        self._writer, self._reconciler, self._clock = writer, reconciler, clock

    def __repr__(self) -> str:
        return "LocalManifestHandoffSupervisorChildCapabilityExecutor()"

    def execute_writer(self, execution):
        if type(execution) is not ExecuteManifestHandoffWriterCapability:
            raise ManifestHandoffRegistryUnavailable
        try:
            request, prepared = execution.request, execution.prepared
            try:
                result = self._writer(
                    self._source, self._target, request.handoff_name.value
                )
                kind = ManifestHandoffWriterProcessKind(result.outcome)
                filename = result.filename
                facts = _facts(result.manifest_sha256, result.file_count)
            except ManifestHandoffUnknown:
                kind = ManifestHandoffWriterProcessKind.OUTCOME_UNKNOWN
                filename = facts = None
            except ManifestHandoffUnavailable:
                kind = ManifestHandoffWriterProcessKind.UNAVAILABLE
                filename = facts = None
            outcome = CompletedManifestHandoffWriterProcess(
                prepared.handle_id, prepared.claim_id, prepared.owner_id,
                kind, _instant(self._clock()), filename, facts,
            )
            return ExecutedManifestHandoffWriterCapability(execution, outcome)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def execute_recovery(self, execution):
        if type(execution) is not ExecuteManifestHandoffRecoveryCapability:
            raise ManifestHandoffRegistryUnavailable
        try:
            request, prepared = execution.request, execution.prepared
            try:
                result = self._reconciler(self._target, request.handoff_name.value)
                kind = ManifestHandoffRecoveryProcessKind(result.outcome)
                filename = result.filename
                facts = _facts(result.manifest_sha256, result.file_count)
            except ManifestReconciliationUnavailable:
                kind = ManifestHandoffRecoveryProcessKind.OUTCOME_UNKNOWN
                filename = facts = None
            outcome = CompletedManifestHandoffRecoveryProcess(
                prepared.handle_id, prepared.claim_id, prepared.owner_id,
                kind, _instant(self._clock()), filename, facts,
            )
            return ExecutedManifestHandoffRecoveryCapability(execution, outcome)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None


def _facts(digest, count):
    if digest is None and count is None:
        return None
    return ManifestHandoffFacts(digest, count)


def _instant(value):
    if (type(value) is not datetime or value.tzinfo is None
            or value.utcoffset() != timezone.utc.utcoffset(value)):
        raise ManifestHandoffRegistryUnavailable
    return value
