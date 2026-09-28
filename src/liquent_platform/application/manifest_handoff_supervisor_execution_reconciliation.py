"""Pure observation-only reconciliation of one child-owned execution."""

from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineState,
    ObservedManifestHandoffSupervisorContainer,
)
from liquent_platform.identity.manifest_handoff_supervisor_execution_reconciliation import (
    ManifestHandoffSupervisorExecutionReconciliation,
    ManifestHandoffSupervisorExecutionReconciliationStatus as Status,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    StartManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BoundManifestHandoffSupervisorRuntime,
    ManifestHandoffSupervisorControlArtifactRole,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_RUNNING = ManifestHandoffSupervisorEngineState.RUNNING
_TERMINAL = {
    ManifestHandoffSupervisorEngineState.EXITED,
    ManifestHandoffSupervisorEngineState.DEAD,
}
_RELEASE_STATES = {
    ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED,
    ManifestHandoffSupervisorJournalState.RUNNING,
    ManifestHandoffSupervisorJournalState.TERMINATION_REQUESTED,
    ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED,
}


class ReadOnlyManifestHandoffSupervisorExecutionReconciler:
    __slots__ = ()

    def __repr__(self) -> str:
        return "ReadOnlyManifestHandoffSupervisorExecutionReconciler()"

    def reconcile(self, *, journal, runtime, gate, observation,
                  release_token, consumed=None, terminal=None):
        journal_types = (ManifestHandoffWriterJournalView, ManifestHandoffRecoveryJournalView)
        if (type(journal) not in journal_types
                or type(runtime) is not BoundManifestHandoffSupervisorRuntime
                or type(gate) is not StartManifestHandoffSupervisorGateWrapper
                or type(observation) is not ObservedManifestHandoffSupervisorContainer
                or type(release_token) is not RecordedManifestHandoffSupervisorControlArtifact
                or (consumed is not None
                    and type(consumed) is not RecordedManifestHandoffSupervisorControlArtifact)
                or (terminal is not None
                    and type(terminal) is not RecordedManifestHandoffSupervisorControlArtifact)):
            raise ManifestHandoffRegistryUnavailable
        try:
            if not self._base_matches(journal, runtime, gate, observation, release_token):
                return self._result(Status.BLOCKED_DIVERGENCE)
            if consumed is not None and not self._artifact_matches(
                    consumed, gate, ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED,
                    journal.release_id, gate.consumed_artifact_id):
                return self._result(Status.BLOCKED_DIVERGENCE)
            if terminal is not None and not self._artifact_matches(
                    terminal, gate, ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE,
                    gate.terminal_observation_id, gate.terminal_artifact_id):
                return self._result(Status.BLOCKED_DIVERGENCE)
            state = observation.state
            if terminal is not None:
                if consumed is None:
                    return self._result(Status.BLOCKED_DIVERGENCE)
                if state in _TERMINAL:
                    return self._result(Status.TERMINAL_EVIDENCE_READY)
                if state is _RUNNING:
                    return self._result(Status.WAITING_FOR_ENGINE_TERMINAL)
                return self._result(Status.BLOCKED_DIVERGENCE)
            if consumed is not None:
                if state is _RUNNING:
                    return self._result(Status.CHILD_CAPABILITY_IN_FLIGHT)
                if state in _TERMINAL:
                    return self._result(Status.AMBIGUOUS_AFTER_CONSUMPTION)
                return self._result(Status.BLOCKED_DIVERGENCE)
            if (journal.state is ManifestHandoffSupervisorJournalState.RUNNING
                    or journal.state is ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED):
                return self._result(Status.BLOCKED_DIVERGENCE)
            if state is _RUNNING:
                return self._result(Status.WAITING_FOR_CHILD_CONSUMPTION)
            return self._result(Status.BLOCKED_DIVERGENCE)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _base_matches(journal, runtime, gate, observation, token):
        handle = journal.registration.handle_id
        return all((
            journal.state in _RELEASE_STATES,
            journal.release_id is not None,
            runtime.handle_id == gate.handle_id == handle,
            runtime.control_directory_id == gate.control_directory_id,
            observation.runtime_container_id == runtime.runtime_container_id,
            observation.creation_id == runtime.creation_id,
            observation.image_digest == runtime.image_digest,
            observation.profile is gate.profile,
            token.handle_id == handle,
            token.role is ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN,
            token.correlation_id == journal.release_id,
        ))

    @staticmethod
    def _artifact_matches(value, gate, role, correlation, artifact_id):
        return all((value.handle_id == gate.handle_id, value.role is role,
                    value.correlation_id == correlation, value.artifact_id == artifact_id))

    @staticmethod
    def _result(status):
        return ManifestHandoffSupervisorExecutionReconciliation(status)
