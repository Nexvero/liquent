"""Restart-safe terminal orchestration for released supervisor jobs."""

from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess, CompletedManifestHandoffWriterProcess,
    PreparedManifestHandoffRecoveryProcess, PreparedManifestHandoffWriterProcess,
    RunningManifestHandoffRecoveryProcess, RunningManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_executor import (
    ExecuteManifestHandoffRecoveryCapability, ExecuteManifestHandoffWriterCapability,
    ExecutedManifestHandoffRecoveryCapability, ExecutedManifestHandoffWriterCapability,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_outcome import (
    InspectManifestHandoffRecoveryCapabilityOutcome,
    InspectManifestHandoffWriterCapabilityOutcome,
    RunningManifestHandoffRecoveryCapability, RunningManifestHandoffWriterCapability,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorTerminalEnvelopeDocument,
    PublishedManifestHandoffSupervisorControlArtifact,
    ReadManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineConflict, ManifestHandoffSupervisorEngineProfile,
    ManifestHandoffSupervisorEngineState, WaitManifestHandoffSupervisorContainer,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    AcceptedManifestHandoffSupervisorReleaseToken,
    CompleteManifestHandoffSupervisorGateWrapper,
    CompletedManifestHandoffSupervisorGateWrapper,
    ManifestHandoffSupervisorGateWrapperConflict,
    ReadyManifestHandoffSupervisorGateWrapper,
    ReleasedManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffRecoveryJournalView, ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorJournalState, ManifestHandoffWriterJournalView,
    RecordManifestHandoffRecoveryJournalTerminal,
    RecordManifestHandoffWriterJournalTerminal,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BoundManifestHandoffSupervisorRuntime, ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorRuntimeConflict,
    RecordManifestHandoffSupervisorTerminalEnvelopeArtifact,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    InspectManifestHandoffSupervisorService, ManifestHandoffRecoveryServiceResult,
    ManifestHandoffSupervisorServiceConflict, ManifestHandoffWriterServiceResult,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_CONFLICTS = (ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorRuntimeConflict, ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorGateWrapperConflict)


class PersistentManifestHandoffSupervisorTerminalService:
    """Observe one released execution and durably correlate terminal facts."""

    __slots__ = ("_journal", "_runtime", "_artifacts", "_gates", "_engine",
        "_wrapper", "_outcomes", "_inspect", "_reader", "_codec")

    def __init__(self, *, journal, runtime_bindings, control_artifacts,
                 gate_bindings, engine, gate_wrapper, outcomes, inspect_service,
                 reader, codec) -> None:
        values = (journal, runtime_bindings, control_artifacts, gate_bindings,
            engine, gate_wrapper, outcomes, inspect_service, reader, codec)
        if any(value is None for value in values):
            raise ManifestHandoffRegistryUnavailable
        (self._journal, self._runtime, self._artifacts, self._gates, self._engine,
            self._wrapper, self._outcomes, self._inspect, self._reader, self._codec) = values

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorTerminalService()"

    def complete_writer(self, command):
        if type(command) is not InspectManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._complete(command,
            inspect_journal=self._journal.inspect_writer_journal,
            inspect_terminal=self._inspect.inspect_writer,
            view_type=ManifestHandoffWriterJournalView,
            profile=ManifestHandoffSupervisorEngineProfile.WRITER,
            prepared_type=PreparedManifestHandoffWriterProcess,
            running_type=RunningManifestHandoffWriterProcess,
            execution_type=ExecuteManifestHandoffWriterCapability,
            inspection_type=InspectManifestHandoffWriterCapabilityOutcome,
            running_observation_type=RunningManifestHandoffWriterCapability,
            executed_type=ExecutedManifestHandoffWriterCapability,
            completed_type=CompletedManifestHandoffWriterProcess,
            inspect_outcome=self._outcomes.inspect_writer_outcome,
            terminal_request_type=RecordManifestHandoffWriterJournalTerminal,
            record_terminal=self._journal.record_writer_terminal,
            result_type=ManifestHandoffWriterServiceResult)

    def complete_recovery(self, command):
        if type(command) is not InspectManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._complete(command,
            inspect_journal=self._journal.inspect_recovery_journal,
            inspect_terminal=self._inspect.inspect_recovery,
            view_type=ManifestHandoffRecoveryJournalView,
            profile=ManifestHandoffSupervisorEngineProfile.RECOVERY,
            prepared_type=PreparedManifestHandoffRecoveryProcess,
            running_type=RunningManifestHandoffRecoveryProcess,
            execution_type=ExecuteManifestHandoffRecoveryCapability,
            inspection_type=InspectManifestHandoffRecoveryCapabilityOutcome,
            running_observation_type=RunningManifestHandoffRecoveryCapability,
            executed_type=ExecutedManifestHandoffRecoveryCapability,
            completed_type=CompletedManifestHandoffRecoveryProcess,
            inspect_outcome=self._outcomes.inspect_recovery_outcome,
            terminal_request_type=RecordManifestHandoffRecoveryJournalTerminal,
            record_terminal=self._journal.record_recovery_terminal,
            result_type=ManifestHandoffRecoveryServiceResult)

    def _complete(self, command, *, inspect_journal, inspect_terminal, view_type,
                  profile, prepared_type, running_type, execution_type,
                  inspection_type, running_observation_type, executed_type,
                  completed_type, inspect_outcome, terminal_request_type,
                  record_terminal, result_type):
        try:
            journal = inspect_journal(command.handle_id)
            if journal is None:
                return None
            if type(journal) is not view_type:
                raise ManifestHandoffRegistryUnavailable
            if journal.state is ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED:
                return inspect_terminal(command)
            if journal.state is not ManifestHandoffSupervisorJournalState.RUNNING:
                return ManifestHandoffSupervisorServiceConflict()

            runtime = self._runtime.resolve_runtime(command.handle_id)
            gate = self._gates.resolve_gate(command.handle_id)
            if (type(runtime) is not BoundManifestHandoffSupervisorRuntime or gate is None
                    or gate.handle_id != runtime.handle_id
                    or gate.handle_id != journal.registration.handle_id
                    or gate.control_directory_id != runtime.control_directory_id
                    or gate.profile is not profile or journal.release_id is None):
                raise ManifestHandoffRegistryUnavailable

            ready_record = self._artifact(command.handle_id,
                ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY)
            token_record = self._artifact(command.handle_id,
                ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN)
            consumed_record = self._artifact(command.handle_id,
                ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED)
            if (ready_record.artifact_id != gate.ready_artifact_id
                    or ready_record.correlation_id != gate.gated_observation_id
                    or token_record.correlation_id != journal.release_id
                    or consumed_record.artifact_id != gate.consumed_artifact_id
                    or consumed_record.correlation_id != journal.release_id):
                raise ManifestHandoffRegistryUnavailable
            ready = ReadyManifestHandoffSupervisorGateWrapper(gate,
                self._publication(gate.control_directory_id, ready_record))
            token = self._wrapper.await_release(ready)
            if (type(token) is not AcceptedManifestHandoffSupervisorReleaseToken
                    or token.token_artifact_id != token_record.artifact_id
                    or token.release_id != journal.release_id):
                raise ManifestHandoffRegistryUnavailable
            released = ReleasedManifestHandoffSupervisorGateWrapper(token,
                self._publication(gate.control_directory_id, consumed_record))

            request = journal.registration.process_request
            prepared = prepared_type(command.handle_id, request.claim_id,
                request.owner_id, ready_record.published_at)
            execution = execution_type(released, prepared, request)
            outcome = inspect_outcome(inspection_type(execution))
            if type(outcome) is running_observation_type:
                process = running_type(command.handle_id, request.claim_id,
                    request.owner_id, journal.observed_at)
                return result_type(journal, runtime, process)
            if type(outcome) is not executed_type or type(outcome.outcome) is not completed_type:
                raise ManifestHandoffRegistryUnavailable

            completed_gate = self._wrapper.publish_terminal(
                CompleteManifestHandoffSupervisorGateWrapper(released, outcome.outcome))
            if type(completed_gate) is ManifestHandoffSupervisorGateWrapperConflict:
                return ManifestHandoffSupervisorServiceConflict()
            if type(completed_gate) is not CompletedManifestHandoffSupervisorGateWrapper:
                raise ManifestHandoffRegistryUnavailable
            recorded = self._artifacts.record_terminal_envelope(
                RecordManifestHandoffSupervisorTerminalEnvelopeArtifact(
                    gate.terminal_artifact_id, command.handle_id,
                    gate.terminal_observation_id, completed_gate.publication.facts))
            if recorded is None:
                raise ManifestHandoffRegistryUnavailable
            if type(recorded) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()

            observation = self._engine.wait_terminal(
                WaitManifestHandoffSupervisorContainer(runtime.runtime_container_id))
            if (observation is None or type(observation) is ManifestHandoffSupervisorEngineConflict
                    or observation.runtime_container_id != runtime.runtime_container_id
                    or observation.creation_id != runtime.creation_id
                    or observation.image_digest != runtime.image_digest
                    or observation.profile is not profile
                    or observation.state not in {ManifestHandoffSupervisorEngineState.EXITED,
                        ManifestHandoffSupervisorEngineState.DEAD}):
                raise ManifestHandoffRegistryUnavailable

            encoded = self._reader.read(ReadManifestHandoffSupervisorControlArtifact(
                gate.control_directory_id,
                ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE))
            if (encoded is None or encoded.artifact_id != recorded.artifact_id
                    or encoded.handle_id != recorded.handle_id
                    or encoded.facts != recorded.facts):
                raise ManifestHandoffRegistryUnavailable
            document = self._codec.decode(encoded)
            if (type(document) is not ManifestHandoffSupervisorTerminalEnvelopeDocument
                    or document.correlation_id != gate.terminal_observation_id
                    or document.outcome != outcome.outcome):
                raise ManifestHandoffRegistryUnavailable

            terminal = record_terminal(terminal_request_type(
                gate.terminal_observation_id, command.handle_id, outcome.outcome))
            if terminal is None:
                raise ManifestHandoffRegistryUnavailable
            if type(terminal) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            if (type(terminal) is not view_type
                    or terminal.state is not ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED):
                raise ManifestHandoffRegistryUnavailable
            return result_type(terminal, runtime, outcome.outcome)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _artifact(self, handle_id, role):
        value = self._artifacts.resolve_artifact_role(handle_id, role)
        if (type(value) is not RecordedManifestHandoffSupervisorControlArtifact
                or value.handle_id != handle_id or value.role is not role):
            raise ManifestHandoffRegistryUnavailable
        return value

    @staticmethod
    def _publication(control_directory_id, record):
        return PublishedManifestHandoffSupervisorControlArtifact(control_directory_id,
            record.artifact_id, record.role, record.facts)
