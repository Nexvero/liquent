"""Read-only reconstruction of persistent supervisor service results."""

from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess, CompletedManifestHandoffWriterProcess,
    PreparedManifestHandoffRecoveryProcess, PreparedManifestHandoffWriterProcess,
    RunningManifestHandoffRecoveryProcess, RunningManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorReadyDocument,
    ManifestHandoffSupervisorReleaseConsumedDocument,
    ManifestHandoffSupervisorReleaseTokenDocument,
    ManifestHandoffSupervisorTerminalEnvelopeDocument,
    ReadManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    InspectManifestHandoffSupervisorContainer, ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorEngineProfile, ManifestHandoffSupervisorEngineState,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffRecoveryJournalView, ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BoundManifestHandoffSupervisorRuntime, ManifestHandoffSupervisorControlArtifactRole,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    InspectManifestHandoffSupervisorService, ManifestHandoffRecoveryServiceResult,
    ManifestHandoffWriterServiceResult,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class PersistentManifestHandoffSupervisorInspectService:
    """Inspect durable and physical facts without performing reconciliation writes."""

    __slots__ = ("_journal", "_runtime", "_artifacts", "_gates", "_engine",
        "_reader", "_codec")

    def __init__(self, *, journal, runtime_bindings, control_artifacts,
                 gate_bindings, engine, reader, codec) -> None:
        dependencies = (journal, runtime_bindings, control_artifacts, gate_bindings,
            engine, reader, codec)
        if any(value is None for value in dependencies):
            raise ManifestHandoffRegistryUnavailable
        (self._journal, self._runtime, self._artifacts, self._gates, self._engine,
            self._reader, self._codec) = dependencies

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorInspectService()"

    def inspect_writer(self, command):
        if type(command) is not InspectManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._inspect(command,
            inspect_journal=self._journal.inspect_writer_journal,
            view_type=ManifestHandoffWriterJournalView,
            profile=ManifestHandoffSupervisorEngineProfile.WRITER,
            prepared_type=PreparedManifestHandoffWriterProcess,
            running_type=RunningManifestHandoffWriterProcess,
            completed_type=CompletedManifestHandoffWriterProcess,
            result_type=ManifestHandoffWriterServiceResult)

    def inspect_recovery(self, command):
        if type(command) is not InspectManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._inspect(command,
            inspect_journal=self._journal.inspect_recovery_journal,
            view_type=ManifestHandoffRecoveryJournalView,
            profile=ManifestHandoffSupervisorEngineProfile.RECOVERY,
            prepared_type=PreparedManifestHandoffRecoveryProcess,
            running_type=RunningManifestHandoffRecoveryProcess,
            completed_type=CompletedManifestHandoffRecoveryProcess,
            result_type=ManifestHandoffRecoveryServiceResult)

    def _inspect(self, command, *, inspect_journal, view_type, profile,
                 prepared_type, running_type, completed_type, result_type):
        try:
            journal = inspect_journal(command.handle_id)
            if journal is None:
                return None
            if type(journal) is not view_type:
                raise ManifestHandoffRegistryUnavailable
            if journal.state not in {
                ManifestHandoffSupervisorJournalState.PREPARED_GATED,
                ManifestHandoffSupervisorJournalState.RUNNING,
                ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED,
            }:
                raise ManifestHandoffRegistryUnavailable

            runtime = self._runtime.resolve_runtime(command.handle_id)
            gate = self._gates.resolve_gate(command.handle_id)
            if (type(runtime) is not BoundManifestHandoffSupervisorRuntime
                    or gate is None
                    or gate.handle_id != runtime.handle_id
                    or gate.handle_id != journal.registration.handle_id
                    or runtime.handle_id != journal.registration.handle_id
                    or gate.control_directory_id != runtime.control_directory_id
                    or gate.profile is not profile):
                raise ManifestHandoffRegistryUnavailable

            ready = self._artifact(command.handle_id,
                ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY)
            self._require_artifact(ready, gate.ready_artifact_id,
                gate.gated_observation_id)
            self._require_document(gate.control_directory_id, ready,
                ManifestHandoffSupervisorReadyDocument)

            observation = self._engine.inspect(
                InspectManifestHandoffSupervisorContainer(runtime.runtime_container_id))
            if (type(observation) is ManifestHandoffSupervisorEngineConflict
                    or not self._observation_matches(observation, runtime, profile)):
                raise ManifestHandoffRegistryUnavailable

            request = journal.registration.process_request
            if journal.state is ManifestHandoffSupervisorJournalState.PREPARED_GATED:
                if observation.state is not ManifestHandoffSupervisorEngineState.RUNNING:
                    raise ManifestHandoffRegistryUnavailable
                process = prepared_type(command.handle_id, request.claim_id,
                    request.owner_id, journal.observed_at)
            elif journal.state is ManifestHandoffSupervisorJournalState.RUNNING:
                if observation.state is not ManifestHandoffSupervisorEngineState.RUNNING:
                    raise ManifestHandoffRegistryUnavailable
                self._require_released(journal, gate)
                process = running_type(command.handle_id, request.claim_id,
                    request.owner_id, journal.observed_at)
            else:
                if observation.state not in {ManifestHandoffSupervisorEngineState.EXITED,
                        ManifestHandoffSupervisorEngineState.DEAD}:
                    raise ManifestHandoffRegistryUnavailable
                if journal.release_id is not None:
                    self._require_released(journal, gate)
                if type(journal.result) is not completed_type:
                    raise ManifestHandoffRegistryUnavailable
                terminal = self._artifact(command.handle_id,
                    ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE)
                self._require_artifact(terminal, gate.terminal_artifact_id,
                    gate.terminal_observation_id)
                document = self._require_document(gate.control_directory_id, terminal,
                    ManifestHandoffSupervisorTerminalEnvelopeDocument)
                if (document.outcome != journal.result
                        or journal.terminal_observation_id != gate.terminal_observation_id):
                    raise ManifestHandoffRegistryUnavailable
                process = journal.result
            return result_type(journal, runtime, process)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _require_released(self, journal, gate):
        if journal.release_id is None:
            raise ManifestHandoffRegistryUnavailable
        token = self._artifact(gate.handle_id,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN)
        consumed = self._artifact(gate.handle_id,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED)
        self._require_artifact(token, token.artifact_id, journal.release_id)
        self._require_artifact(consumed, gate.consumed_artifact_id, journal.release_id)
        token_document = self._require_document(gate.control_directory_id, token,
            ManifestHandoffSupervisorReleaseTokenDocument)
        consumed_document = self._require_document(gate.control_directory_id, consumed,
            ManifestHandoffSupervisorReleaseConsumedDocument)
        if token_document.artifact_id == consumed_document.artifact_id:
            raise ManifestHandoffRegistryUnavailable

    def _artifact(self, handle_id, role):
        value = self._artifacts.resolve_artifact_role(handle_id, role)
        if (type(value) is not RecordedManifestHandoffSupervisorControlArtifact
                or value.role is not role or value.handle_id != handle_id):
            raise ManifestHandoffRegistryUnavailable
        return value

    @staticmethod
    def _require_artifact(record, artifact_id, correlation_id):
        if (record.artifact_id != artifact_id
                or record.correlation_id != correlation_id):
            raise ManifestHandoffRegistryUnavailable

    def _require_document(self, control_directory_id, record, document_type):
        encoded = self._reader.read(ReadManifestHandoffSupervisorControlArtifact(
            control_directory_id, record.role))
        if (encoded is None or encoded.artifact_id != record.artifact_id
                or encoded.handle_id != record.handle_id
                or encoded.role is not record.role or encoded.facts != record.facts):
            raise ManifestHandoffRegistryUnavailable
        document = self._codec.decode(encoded)
        if (type(document) is not document_type
                or document.artifact_id != record.artifact_id
                or document.handle_id != record.handle_id
                or document.correlation_id != record.correlation_id):
            raise ManifestHandoffRegistryUnavailable
        return document

    @staticmethod
    def _observation_matches(observation, runtime, profile):
        return (observation is not None
            and observation.runtime_container_id == runtime.runtime_container_id
            and observation.creation_id == runtime.creation_id
            and observation.image_digest == runtime.image_digest
            and observation.profile is profile)
