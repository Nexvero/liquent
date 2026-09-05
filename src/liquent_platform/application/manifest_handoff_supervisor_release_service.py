"""Restart-safe release orchestration for persistent supervisor jobs."""

from liquent_platform.identity.manifest_handoff_supervisor import (
    PreparedManifestHandoffRecoveryProcess, PreparedManifestHandoffWriterProcess,
    RunningManifestHandoffRecoveryProcess, RunningManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_executor import (
    ExecuteManifestHandoffRecoveryCapability, ExecuteManifestHandoffWriterCapability,
    ExecutedManifestHandoffRecoveryCapability, ExecutedManifestHandoffWriterCapability,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorControlArtifactConflict,
    ManifestHandoffSupervisorReleaseTokenDocument,
    PublishManifestHandoffSupervisorControlArtifact,
    PublishedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    InspectManifestHandoffSupervisorContainer, ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorEngineProfile, ManifestHandoffSupervisorEngineState,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    AcceptedManifestHandoffSupervisorReleaseToken,
    ManifestHandoffSupervisorGateWrapperConflict,
    ReadyManifestHandoffSupervisorGateWrapper,
    ReleasedManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    CommitManifestHandoffSupervisorGateRelease,
    ManifestHandoffRecoveryJournalView, ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorJournalState, ManifestHandoffWriterJournalView,
    RecordManifestHandoffSupervisorRunning,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BoundManifestHandoffSupervisorRuntime, ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorRuntimeConflict,
    RecordManifestHandoffSupervisorReleaseConsumedArtifact,
    RecordManifestHandoffSupervisorReleaseTokenArtifact,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    ManifestHandoffRecoveryServiceResult, ManifestHandoffSupervisorGateBindingConflict,
    ManifestHandoffSupervisorServiceConflict, ManifestHandoffWriterServiceResult,
    ReleaseManifestHandoffSupervisorService,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_CONFLICTS = (ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorRuntimeConflict, ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorGateWrapperConflict, ManifestHandoffSupervisorGateBindingConflict,
    ManifestHandoffSupervisorControlArtifactConflict)


class PersistentManifestHandoffSupervisorReleaseService:
    """Advance only the closed release prefix and execute capability once."""

    __slots__ = ("_journal", "_runtime", "_artifacts", "_gates", "_engine",
        "_wrapper", "_codec", "_publisher", "_executor")

    def __init__(self, *, journal, runtime_bindings, control_artifacts,
                 gate_bindings, engine, gate_wrapper, codec, publisher, executor) -> None:
        dependencies = (journal, runtime_bindings, control_artifacts, gate_bindings,
            engine, gate_wrapper, codec, publisher, executor)
        if any(value is None for value in dependencies):
            raise ManifestHandoffRegistryUnavailable
        (self._journal, self._runtime, self._artifacts, self._gates, self._engine,
            self._wrapper, self._codec, self._publisher, self._executor) = dependencies

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorReleaseService()"

    def release_writer(self, command):
        if type(command) is not ReleaseManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._release(command, profile=ManifestHandoffSupervisorEngineProfile.WRITER,
            inspect_journal=self._journal.inspect_writer_journal,
            commit_release=self._journal.commit_writer_release,
            record_running=self._journal.record_writer_running,
            view_type=ManifestHandoffWriterJournalView,
            prepared_type=PreparedManifestHandoffWriterProcess,
            running_type=RunningManifestHandoffWriterProcess,
            execution_type=ExecuteManifestHandoffWriterCapability,
            executed_type=ExecutedManifestHandoffWriterCapability,
            execute=self._executor.execute_writer,
            result_type=ManifestHandoffWriterServiceResult)

    def release_recovery(self, command):
        if type(command) is not ReleaseManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._release(command, profile=ManifestHandoffSupervisorEngineProfile.RECOVERY,
            inspect_journal=self._journal.inspect_recovery_journal,
            commit_release=self._journal.commit_recovery_release,
            record_running=self._journal.record_recovery_running,
            view_type=ManifestHandoffRecoveryJournalView,
            prepared_type=PreparedManifestHandoffRecoveryProcess,
            running_type=RunningManifestHandoffRecoveryProcess,
            execution_type=ExecuteManifestHandoffRecoveryCapability,
            executed_type=ExecutedManifestHandoffRecoveryCapability,
            execute=self._executor.execute_recovery,
            result_type=ManifestHandoffRecoveryServiceResult)

    def _release(self, command, *, profile, inspect_journal, commit_release,
                 record_running, view_type, prepared_type, running_type,
                 execution_type, executed_type, execute, result_type):
        try:
            journal = inspect_journal(command.handle_id)
            if journal is None:
                return None
            if type(journal) is not view_type:
                raise ManifestHandoffRegistryUnavailable
            if journal.state not in {ManifestHandoffSupervisorJournalState.PREPARED_GATED,
                    ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED,
                    ManifestHandoffSupervisorJournalState.RUNNING}:
                return ManifestHandoffSupervisorServiceConflict()
            if (journal.release_id is not None and journal.release_id != command.release_id):
                return ManifestHandoffSupervisorServiceConflict()

            runtime = self._runtime.resolve_runtime(command.handle_id)
            gate = self._gates.resolve_gate(command.handle_id)
            if runtime is None or gate is None:
                raise ManifestHandoffRegistryUnavailable
            if not self._bindings_match(runtime, gate, journal, profile):
                return ManifestHandoffSupervisorServiceConflict()
            ready_record = self._artifact(command.handle_id,
                ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY)
            ready = self._ready(gate, ready_record)

            if journal.state is ManifestHandoffSupervisorJournalState.PREPARED_GATED:
                journal = commit_release(CommitManifestHandoffSupervisorGateRelease(
                    command.release_id, command.handle_id))
                if journal is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(journal) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
                if type(journal) is not view_type:
                    raise ManifestHandoffRegistryUnavailable

            already_running = journal.state is ManifestHandoffSupervisorJournalState.RUNNING
            if journal.state not in {ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED,
                    ManifestHandoffSupervisorJournalState.RUNNING}:
                return ManifestHandoffSupervisorServiceConflict()
            if journal.release_id != command.release_id:
                return ManifestHandoffSupervisorServiceConflict()

            if already_running:
                released = self._reconstruct_released(command, ready)
            else:
                released = self._publish_release(command, ready)
                if type(released) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()

            observation = self._engine.inspect(
                InspectManifestHandoffSupervisorContainer(runtime.runtime_container_id))
            if observation is None:
                raise ManifestHandoffRegistryUnavailable
            if type(observation) in _CONFLICTS or not self._running_matches(
                    observation, runtime, profile):
                return ManifestHandoffSupervisorServiceConflict()

            if not already_running:
                journal = record_running(RecordManifestHandoffSupervisorRunning(
                    command.running_observation_id, command.handle_id))
                if journal is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(journal) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
                if type(journal) is not view_type:
                    raise ManifestHandoffRegistryUnavailable
                prepared = prepared_type(command.handle_id,
                    journal.registration.process_request.claim_id,
                    journal.registration.process_request.owner_id,
                    ready_record.published_at)
                execution = execution_type(released, prepared,
                    journal.registration.process_request)
                executed = execute(execution)
                if type(executed) is not executed_type:
                    raise ManifestHandoffRegistryUnavailable
            else:
                retry = record_running(RecordManifestHandoffSupervisorRunning(
                    command.running_observation_id, command.handle_id))
                if type(retry) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
                if type(retry) is not view_type:
                    raise ManifestHandoffRegistryUnavailable
                journal = retry

            process = running_type(command.handle_id,
                journal.registration.process_request.claim_id,
                journal.registration.process_request.owner_id, journal.observed_at)
            return result_type(journal, runtime, process)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _publish_release(self, command, ready):
        document = ManifestHandoffSupervisorReleaseTokenDocument(
            command.token_artifact_id, command.handle_id, command.release_id)
        encoded = self._codec.encode(document)
        publication = self._publisher.publish(PublishManifestHandoffSupervisorControlArtifact(
            ready.binding.control_directory_id, encoded))
        if type(publication) is ManifestHandoffSupervisorControlArtifactConflict:
            return publication
        token_record = self._artifacts.record_release_token(
            RecordManifestHandoffSupervisorReleaseTokenArtifact(command.token_artifact_id,
                command.handle_id, command.release_id, publication.facts))
        if token_record is None:
            raise ManifestHandoffRegistryUnavailable
        if type(token_record) in _CONFLICTS:
            return token_record
        token = self._wrapper.await_release(ready)
        if (type(token) is not AcceptedManifestHandoffSupervisorReleaseToken
                or token.token_artifact_id != command.token_artifact_id
                or token.release_id != command.release_id):
            raise ManifestHandoffRegistryUnavailable
        released = self._wrapper.publish_consumed(token)
        if type(released) is ManifestHandoffSupervisorGateWrapperConflict:
            return released
        consumed = self._artifacts.record_release_consumed(
            RecordManifestHandoffSupervisorReleaseConsumedArtifact(
                ready.binding.consumed_artifact_id, command.handle_id,
                command.release_id, released.publication.facts))
        if consumed is None:
            raise ManifestHandoffRegistryUnavailable
        if type(consumed) in _CONFLICTS:
            return consumed
        return released

    def _reconstruct_released(self, command, ready):
        token_record = self._artifact(command.handle_id,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN)
        consumed = self._artifact(command.handle_id,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED)
        if (token_record.artifact_id != command.token_artifact_id
                or token_record.correlation_id != command.release_id
                or consumed.correlation_id != command.release_id
                or consumed.artifact_id != ready.binding.consumed_artifact_id):
            raise ManifestHandoffRegistryUnavailable
        token = self._wrapper.await_release(ready)
        if (type(token) is not AcceptedManifestHandoffSupervisorReleaseToken
                or token.token_artifact_id != command.token_artifact_id
                or token.release_id != command.release_id):
            raise ManifestHandoffRegistryUnavailable
        publication = PublishedManifestHandoffSupervisorControlArtifact(
            ready.binding.control_directory_id, consumed.artifact_id,
            consumed.role, consumed.facts)
        return ReleasedManifestHandoffSupervisorGateWrapper(token, publication)

    def _artifact(self, handle_id, role):
        record = self._artifacts.resolve_artifact_role(handle_id, role)
        if type(record) is not RecordedManifestHandoffSupervisorControlArtifact:
            raise ManifestHandoffRegistryUnavailable
        return record

    @staticmethod
    def _ready(gate, record):
        if (record.artifact_id != gate.ready_artifact_id
                or record.correlation_id != gate.gated_observation_id
                or record.role is not ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY):
            raise ManifestHandoffRegistryUnavailable
        publication = PublishedManifestHandoffSupervisorControlArtifact(
            gate.control_directory_id, record.artifact_id, record.role, record.facts)
        return ReadyManifestHandoffSupervisorGateWrapper(gate, publication)

    @staticmethod
    def _bindings_match(runtime, gate, journal, profile):
        return (type(runtime) is BoundManifestHandoffSupervisorRuntime
            and gate.handle_id == runtime.handle_id == journal.registration.handle_id
            and gate.control_directory_id == runtime.control_directory_id
            and gate.profile is profile)

    @staticmethod
    def _running_matches(observation, runtime, profile):
        return (observation.runtime_container_id == runtime.runtime_container_id
            and observation.creation_id == runtime.creation_id
            and observation.image_digest == runtime.image_digest
            and observation.profile is profile
            and observation.state is ManifestHandoffSupervisorEngineState.RUNNING)
