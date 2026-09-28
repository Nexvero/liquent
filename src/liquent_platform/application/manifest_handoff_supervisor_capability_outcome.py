"""Read-only inspect and bounded wait over controlled supervisor state."""

from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
    RunningManifestHandoffRecoveryProcess,
    RunningManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_executor import (
    ExecutedManifestHandoffRecoveryCapability,
    ExecutedManifestHandoffWriterCapability,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_outcome import (
    InspectManifestHandoffRecoveryCapabilityOutcome,
    InspectManifestHandoffWriterCapabilityOutcome,
    RunningManifestHandoffRecoveryCapability,
    RunningManifestHandoffWriterCapability,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ControlledManifestHandoffSupervisorCapabilityOutcome:
    """Observe an existing execution without release, start, or termination."""

    __slots__ = ("_writer", "_recovery", "_maximum", "_pause")

    def __init__(self, *, writer_supervisor, recovery_supervisor,
                 maximum_observations: int, pause) -> None:
        if (writer_supervisor is None or recovery_supervisor is None
                or type(maximum_observations) is not int
                or not 1 <= maximum_observations <= 10_000 or pause is None):
            raise ManifestHandoffRegistryUnavailable
        self._writer = writer_supervisor
        self._recovery = recovery_supervisor
        self._maximum = maximum_observations
        self._pause = pause

    def __repr__(self) -> str:
        return "ControlledManifestHandoffSupervisorCapabilityOutcome()"

    def inspect_writer_outcome(self, request):
        if type(request) is not InspectManifestHandoffWriterCapabilityOutcome:
            raise ManifestHandoffRegistryUnavailable
        prepared = request.execution.prepared
        try:
            state = self._writer.inspect_writer(
                prepared.handle_id, prepared.claim_id, prepared.owner_id)
            if type(state) is RunningManifestHandoffWriterProcess:
                return RunningManifestHandoffWriterCapability(request, state)
            if type(state) is CompletedManifestHandoffWriterProcess:
                return ExecutedManifestHandoffWriterCapability(request.execution, state)
            raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def inspect_recovery_outcome(self, request):
        if type(request) is not InspectManifestHandoffRecoveryCapabilityOutcome:
            raise ManifestHandoffRegistryUnavailable
        prepared = request.execution.prepared
        try:
            state = self._recovery.inspect_recovery(
                prepared.handle_id, prepared.claim_id, prepared.owner_id)
            if type(state) is RunningManifestHandoffRecoveryProcess:
                return RunningManifestHandoffRecoveryCapability(request, state)
            if type(state) is CompletedManifestHandoffRecoveryProcess:
                return ExecutedManifestHandoffRecoveryCapability(request.execution, state)
            raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def wait_writer_outcome(self, request):
        for index in range(self._maximum):
            observed = self.inspect_writer_outcome(request)
            if type(observed) is ExecutedManifestHandoffWriterCapability:
                return observed
            if index + 1 < self._maximum:
                self._safe_pause()
        raise ManifestHandoffRegistryUnavailable

    def wait_recovery_outcome(self, request):
        for index in range(self._maximum):
            observed = self.inspect_recovery_outcome(request)
            if type(observed) is ExecutedManifestHandoffRecoveryCapability:
                return observed
            if index + 1 < self._maximum:
                self._safe_pause()
        raise ManifestHandoffRegistryUnavailable

    def _safe_pause(self):
        try:
            if self._pause() is not None:
                raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
