"""Observation-only parent terminalization from direct child envelope and engine state."""

from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    InspectManifestHandoffSupervisorContainer,
    ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorEngineProfile,
    ManifestHandoffSupervisorEngineState,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
    RecordManifestHandoffRecoveryJournalTerminal,
    RecordManifestHandoffWriterJournalTerminal,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BoundManifestHandoffSupervisorRuntime,
    ManifestHandoffSupervisorRuntimeConflict,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    InspectManifestHandoffSupervisorService,
    ManifestHandoffRecoveryServiceResult,
    ManifestHandoffSupervisorServiceConflict,
    ManifestHandoffWriterServiceResult,
)
from liquent_platform.identity.manifest_handoff_supervisor_terminal_observation import (
    RecordedManifestHandoffSupervisorTerminalArtifact,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_CONFLICTS = (
    ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorRuntimeConflict,
    ManifestHandoffSupervisorEngineConflict,
)
_ENGINE_TERMINAL = {
    ManifestHandoffSupervisorEngineState.EXITED,
    ManifestHandoffSupervisorEngineState.DEAD,
}


class ObservationOnlyManifestHandoffSupervisorTerminalService:
    __slots__ = ("_engine", "_gates", "_journal", "_recorder", "_runtime")

    def __init__(self, *, journal, runtime_bindings, gate_bindings, engine,
                 wrapper_artifact_recorder) -> None:
        values = (journal, runtime_bindings, gate_bindings, engine,
                  wrapper_artifact_recorder)
        if any(value is None for value in values):
            raise ManifestHandoffRegistryUnavailable
        self._journal, self._runtime, self._gates, self._engine, self._recorder = values

    def __repr__(self) -> str:
        return "ObservationOnlyManifestHandoffSupervisorTerminalService()"

    def complete_writer(self, command):
        return self._entry(command, ManifestHandoffSupervisorEngineProfile.WRITER,
            self._journal.inspect_writer_journal, self._journal.record_writer_terminal,
            ManifestHandoffWriterJournalView, CompletedManifestHandoffWriterProcess,
            RecordManifestHandoffWriterJournalTerminal,
            ManifestHandoffWriterServiceResult)

    def complete_recovery(self, command):
        return self._entry(command, ManifestHandoffSupervisorEngineProfile.RECOVERY,
            self._journal.inspect_recovery_journal, self._journal.record_recovery_terminal,
            ManifestHandoffRecoveryJournalView, CompletedManifestHandoffRecoveryProcess,
            RecordManifestHandoffRecoveryJournalTerminal,
            ManifestHandoffRecoveryServiceResult)

    def _entry(self, command, *arguments):
        if type(command) is not InspectManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._complete(command, *arguments)

    def _complete(self, command, profile, inspect_journal, record_terminal,
                  view_type, outcome_type, transition_type, result_type):
        try:
            journal = inspect_journal(command.handle_id)
            if journal is None:
                return None
            if type(journal) is not view_type:
                raise ManifestHandoffRegistryUnavailable
            runtime = self._runtime.resolve_runtime(command.handle_id)
            gate = self._gates.resolve_gate(command.handle_id)
            if not self._bindings(journal, runtime, gate, profile):
                return ManifestHandoffSupervisorServiceConflict()
            if journal.state is ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED:
                return result_type(journal, runtime, journal.result)
            if journal.state not in {
                ManifestHandoffSupervisorJournalState.RUNNING,
                ManifestHandoffSupervisorJournalState.TERMINATION_REQUESTED,
            }:
                return ManifestHandoffSupervisorServiceConflict()
            terminal = self._recorder.record_terminal(gate)
            if terminal is None:
                return None
            if type(terminal) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            if type(terminal) is not RecordedManifestHandoffSupervisorTerminalArtifact:
                raise ManifestHandoffRegistryUnavailable
            outcome = terminal.observation.document.outcome
            if type(outcome) is not outcome_type or outcome.handle_id != command.handle_id:
                return ManifestHandoffSupervisorServiceConflict()
            observation = self._engine.inspect(
                InspectManifestHandoffSupervisorContainer(runtime.runtime_container_id)
            )
            if observation is None:
                raise ManifestHandoffRegistryUnavailable
            if (type(observation) in _CONFLICTS
                    or observation.runtime_container_id != runtime.runtime_container_id
                    or observation.creation_id != runtime.creation_id
                    or observation.image_digest != runtime.image_digest
                    or observation.profile is not profile):
                return ManifestHandoffSupervisorServiceConflict()
            if observation.state is ManifestHandoffSupervisorEngineState.RUNNING:
                return None
            if observation.state not in _ENGINE_TERMINAL:
                return ManifestHandoffSupervisorServiceConflict()
            journal = record_terminal(transition_type(
                gate.terminal_observation_id, command.handle_id, outcome
            ))
            if journal is None:
                raise ManifestHandoffRegistryUnavailable
            if type(journal) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            if (type(journal) is not view_type
                    or journal.state is not ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED
                    or journal.result != outcome):
                raise ManifestHandoffRegistryUnavailable
            return result_type(journal, runtime, outcome)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _bindings(journal, runtime, gate, profile):
        return (type(runtime) is BoundManifestHandoffSupervisorRuntime
                and gate is not None
                and runtime.handle_id == gate.handle_id == journal.registration.handle_id
                and runtime.control_directory_id == gate.control_directory_id
                and gate.profile is profile)
