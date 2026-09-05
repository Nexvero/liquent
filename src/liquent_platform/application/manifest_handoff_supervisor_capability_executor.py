"""Fail-closed compatibility adapter for controlled supervisor primitives."""

from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_executor import (
    ExecuteManifestHandoffRecoveryCapability,
    ExecuteManifestHandoffWriterCapability,
    ExecutedManifestHandoffRecoveryCapability,
    ExecutedManifestHandoffWriterCapability,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ControlledManifestHandoffSupervisorCapabilityExecutor:
    """Delegate once and accept only a directly terminal controlled outcome."""

    __slots__ = ("_writer", "_recovery")

    def __init__(self, *, writer_supervisor, recovery_supervisor) -> None:
        if writer_supervisor is None or recovery_supervisor is None:
            raise ManifestHandoffRegistryUnavailable
        self._writer = writer_supervisor
        self._recovery = recovery_supervisor

    def __repr__(self) -> str:
        return "ControlledManifestHandoffSupervisorCapabilityExecutor()"

    def execute_writer(self, request):
        if type(request) is not ExecuteManifestHandoffWriterCapability:
            raise ManifestHandoffRegistryUnavailable
        prepared = request.prepared
        try:
            outcome = self._writer.release_writer(
                prepared.handle_id, prepared.claim_id, prepared.owner_id)
            if type(outcome) is not CompletedManifestHandoffWriterProcess:
                raise ManifestHandoffRegistryUnavailable
            return ExecutedManifestHandoffWriterCapability(request, outcome)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def execute_recovery(self, request):
        if type(request) is not ExecuteManifestHandoffRecoveryCapability:
            raise ManifestHandoffRegistryUnavailable
        prepared = request.prepared
        try:
            outcome = self._recovery.release_recovery(
                prepared.handle_id, prepared.claim_id, prepared.owner_id)
            if type(outcome) is not CompletedManifestHandoffRecoveryProcess:
                raise ManifestHandoffRegistryUnavailable
            return ExecutedManifestHandoffRecoveryCapability(request, outcome)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
