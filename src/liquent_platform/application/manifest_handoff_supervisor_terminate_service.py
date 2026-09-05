"""Durable-before-signal termination for persistent supervisor jobs."""

from collections.abc import Callable
from datetime import datetime, timezone

from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess, CompletedManifestHandoffWriterProcess,
    ManifestHandoffRecoveryProcessKind, ManifestHandoffWriterProcessKind,
    PreparedManifestHandoffRecoveryProcess, PreparedManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_executor import (
    ExecuteManifestHandoffRecoveryCapability, ExecuteManifestHandoffWriterCapability,
    ExecutedManifestHandoffRecoveryCapability, ExecutedManifestHandoffWriterCapability,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_outcome import (
    InspectManifestHandoffRecoveryCapabilityOutcome,
    InspectManifestHandoffWriterCapabilityOutcome,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorTerminalEnvelopeDocument,
    PublishedManifestHandoffSupervisorControlArtifact,
    ReadManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    AcceptedManifestHandoffSupervisorTermination,
    ManifestHandoffSupervisorEngineConflict, ManifestHandoffSupervisorEngineProfile,
    ManifestHandoffSupervisorEngineState, TerminateManifestHandoffSupervisorContainer,
    WaitManifestHandoffSupervisorContainer,
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
    RequestManifestHandoffSupervisorTermination,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BoundManifestHandoffSupervisorRuntime, ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorRuntimeConflict,
    RecordManifestHandoffSupervisorTerminalEnvelopeArtifact,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    InspectManifestHandoffSupervisorService,
    ManifestHandoffRecoveryServiceResult, ManifestHandoffSupervisorServiceConflict,
    ManifestHandoffWriterServiceResult, TerminateManifestHandoffSupervisorService,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_CONFLICTS = (ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorRuntimeConflict, ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorGateWrapperConflict)


class PersistentManifestHandoffSupervisorTerminateService:
    """Persist termination intent before touching the bound engine container."""

    __slots__ = ("_journal", "_runtime", "_artifacts", "_gates", "_engine",
        "_wrapper", "_outcomes", "_inspect", "_reader", "_codec", "_clock")

    def __init__(self, *, journal, runtime_bindings, control_artifacts,
                 gate_bindings, engine, gate_wrapper, outcomes, inspect_service,
                 reader, codec, clock: Callable[[], datetime] | None = None) -> None:
        values = (journal, runtime_bindings, control_artifacts, gate_bindings,
            engine, gate_wrapper, outcomes, inspect_service, reader, codec)
        if any(value is None for value in values):
            raise ManifestHandoffRegistryUnavailable
        (self._journal, self._runtime, self._artifacts, self._gates, self._engine,
            self._wrapper, self._outcomes, self._inspect, self._reader, self._codec) = values
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorTerminateService()"

    def terminate_writer(self, command):
        if type(command) is not TerminateManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._terminate(command,
            inspect_journal=self._journal.inspect_writer_journal,
            inspect_terminal=self._inspect.inspect_writer,
            request_termination=self._journal.request_writer_termination,
            record_terminal=self._journal.record_writer_terminal,
            view_type=ManifestHandoffWriterJournalView,
            profile=ManifestHandoffSupervisorEngineProfile.WRITER,
            prepared_type=PreparedManifestHandoffWriterProcess,
            execution_type=ExecuteManifestHandoffWriterCapability,
            inspection_type=InspectManifestHandoffWriterCapabilityOutcome,
            executed_type=ExecutedManifestHandoffWriterCapability,
            wait_outcome=self._outcomes.wait_writer_outcome,
            unknown=self._unknown_writer,
            terminal_request_type=RecordManifestHandoffWriterJournalTerminal,
            result_type=ManifestHandoffWriterServiceResult)

    def terminate_recovery(self, command):
        if type(command) is not TerminateManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._terminate(command,
            inspect_journal=self._journal.inspect_recovery_journal,
            inspect_terminal=self._inspect.inspect_recovery,
            request_termination=self._journal.request_recovery_termination,
            record_terminal=self._journal.record_recovery_terminal,
            view_type=ManifestHandoffRecoveryJournalView,
            profile=ManifestHandoffSupervisorEngineProfile.RECOVERY,
            prepared_type=PreparedManifestHandoffRecoveryProcess,
            execution_type=ExecuteManifestHandoffRecoveryCapability,
            inspection_type=InspectManifestHandoffRecoveryCapabilityOutcome,
            executed_type=ExecutedManifestHandoffRecoveryCapability,
            wait_outcome=self._outcomes.wait_recovery_outcome,
            unknown=self._unknown_recovery,
            terminal_request_type=RecordManifestHandoffRecoveryJournalTerminal,
            result_type=ManifestHandoffRecoveryServiceResult)

    def _terminate(self, command, *, inspect_journal, inspect_terminal,
                   request_termination, record_terminal, view_type, profile,
                   prepared_type, execution_type, inspection_type, executed_type,
                   wait_outcome, unknown, terminal_request_type, result_type):
        try:
            journal = inspect_journal(command.handle_id)
            if journal is None:
                return None
            if type(journal) is not view_type:
                raise ManifestHandoffRegistryUnavailable
            if journal.state is ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED:
                return inspect_terminal(InspectManifestHandoffSupervisorService(command.handle_id))
            if journal.state not in {ManifestHandoffSupervisorJournalState.PREPARED_GATED,
                    ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED,
                    ManifestHandoffSupervisorJournalState.RUNNING,
                    ManifestHandoffSupervisorJournalState.TERMINATION_REQUESTED}:
                return ManifestHandoffSupervisorServiceConflict()

            runtime = self._runtime.resolve_runtime(command.handle_id)
            gate = self._gates.resolve_gate(command.handle_id)
            if (type(runtime) is not BoundManifestHandoffSupervisorRuntime or gate is None
                    or gate.handle_id != runtime.handle_id
                    or gate.handle_id != journal.registration.handle_id
                    or gate.control_directory_id != runtime.control_directory_id
                    or gate.profile is not profile):
                raise ManifestHandoffRegistryUnavailable
            ready_record = self._artifact(command.handle_id,
                ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY)
            if (ready_record.artifact_id != gate.ready_artifact_id
                    or ready_record.correlation_id != gate.gated_observation_id):
                raise ManifestHandoffRegistryUnavailable
            ready = ReadyManifestHandoffSupervisorGateWrapper(gate,
                self._publication(gate.control_directory_id, ready_record))
            released = self._released(journal, ready)

            if journal.state is not ManifestHandoffSupervisorJournalState.TERMINATION_REQUESTED:
                journal = request_termination(RequestManifestHandoffSupervisorTermination(
                    command.terminate_id, command.handle_id))
                if journal is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(journal) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
            elif journal.terminate_id != command.terminate_id:
                return ManifestHandoffSupervisorServiceConflict()
            if (type(journal) is not view_type
                    or journal.state is not ManifestHandoffSupervisorJournalState.TERMINATION_REQUESTED):
                raise ManifestHandoffRegistryUnavailable

            accepted = self._engine.terminate(TerminateManifestHandoffSupervisorContainer(
                runtime.runtime_container_id, command.terminate_id))
            if type(accepted) is ManifestHandoffSupervisorEngineConflict:
                return ManifestHandoffSupervisorServiceConflict()
            if (type(accepted) is not AcceptedManifestHandoffSupervisorTermination
                    or accepted.runtime_container_id != runtime.runtime_container_id
                    or accepted.terminate_id != command.terminate_id):
                raise ManifestHandoffRegistryUnavailable
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

            request = journal.registration.process_request
            if released is None:
                outcome = unknown(command.handle_id, request, self._utc())
                terminal_gate = ready
            else:
                prepared = prepared_type(command.handle_id, request.claim_id,
                    request.owner_id, ready_record.published_at)
                execution = execution_type(released, prepared, request)
                executed = wait_outcome(inspection_type(execution))
                if type(executed) is not executed_type:
                    raise ManifestHandoffRegistryUnavailable
                outcome = executed.outcome
                terminal_gate = released

            completed = self._wrapper.publish_terminal(
                CompleteManifestHandoffSupervisorGateWrapper(terminal_gate, outcome))
            if type(completed) is ManifestHandoffSupervisorGateWrapperConflict:
                return ManifestHandoffSupervisorServiceConflict()
            if type(completed) is not CompletedManifestHandoffSupervisorGateWrapper:
                raise ManifestHandoffRegistryUnavailable
            recorded = self._artifacts.record_terminal_envelope(
                RecordManifestHandoffSupervisorTerminalEnvelopeArtifact(
                    gate.terminal_artifact_id, command.handle_id,
                    gate.terminal_observation_id, completed.publication.facts))
            if recorded is None:
                raise ManifestHandoffRegistryUnavailable
            if type(recorded) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            self._verify_envelope(gate, recorded, outcome)
            terminal = record_terminal(terminal_request_type(
                gate.terminal_observation_id, command.handle_id, outcome))
            if terminal is None:
                raise ManifestHandoffRegistryUnavailable
            if type(terminal) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            return result_type(terminal, runtime, outcome)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _released(self, journal, ready):
        if journal.release_id is None:
            return None
        token_record = self._artifacts.resolve_artifact_role(ready.binding.handle_id,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN)
        consumed = self._artifacts.resolve_artifact_role(ready.binding.handle_id,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED)
        if (type(token_record) is not RecordedManifestHandoffSupervisorControlArtifact
                or type(consumed) is not RecordedManifestHandoffSupervisorControlArtifact
                or token_record.correlation_id != journal.release_id
                or consumed.correlation_id != journal.release_id
                or consumed.artifact_id != ready.binding.consumed_artifact_id):
            raise ManifestHandoffRegistryUnavailable
        token = self._wrapper.await_release(ready)
        if (type(token) is not AcceptedManifestHandoffSupervisorReleaseToken
                or token.token_artifact_id != token_record.artifact_id
                or token.release_id != journal.release_id):
            raise ManifestHandoffRegistryUnavailable
        return ReleasedManifestHandoffSupervisorGateWrapper(token,
            self._publication(ready.binding.control_directory_id, consumed))

    def _artifact(self, handle_id, role):
        value = self._artifacts.resolve_artifact_role(handle_id, role)
        if (type(value) is not RecordedManifestHandoffSupervisorControlArtifact
                or value.handle_id != handle_id or value.role is not role):
            raise ManifestHandoffRegistryUnavailable
        return value

    def _verify_envelope(self, gate, record, outcome):
        encoded = self._reader.read(ReadManifestHandoffSupervisorControlArtifact(
            gate.control_directory_id,
            ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE))
        if (encoded is None or encoded.artifact_id != record.artifact_id
                or encoded.handle_id != record.handle_id or encoded.facts != record.facts):
            raise ManifestHandoffRegistryUnavailable
        document = self._codec.decode(encoded)
        if (type(document) is not ManifestHandoffSupervisorTerminalEnvelopeDocument
                or document.correlation_id != gate.terminal_observation_id
                or document.outcome != outcome):
            raise ManifestHandoffRegistryUnavailable

    def _utc(self):
        value = self._clock()
        if (type(value) is not datetime or value.tzinfo is None
                or value.utcoffset() != timezone.utc.utcoffset(value)):
            raise ManifestHandoffRegistryUnavailable
        return value

    @staticmethod
    def _unknown_writer(handle_id, request, ended_at):
        return CompletedManifestHandoffWriterProcess(handle_id, request.claim_id,
            request.owner_id, ManifestHandoffWriterProcessKind.OUTCOME_UNKNOWN, ended_at)

    @staticmethod
    def _unknown_recovery(handle_id, request, ended_at):
        return CompletedManifestHandoffRecoveryProcess(handle_id, request.claim_id,
            request.owner_id, ManifestHandoffRecoveryProcessKind.OUTCOME_UNKNOWN, ended_at)

    @staticmethod
    def _publication(control_directory_id, record):
        return PublishedManifestHandoffSupervisorControlArtifact(control_directory_id,
            record.artifact_id, record.role, record.facts)
