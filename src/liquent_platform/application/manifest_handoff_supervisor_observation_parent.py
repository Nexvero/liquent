"""Parallel observation-only parent completion for child-owned supervisor work."""

from liquent_platform.identity.manifest_handoff_supervisor import (
    PreparedManifestHandoffRecoveryProcess,
    PreparedManifestHandoffWriterProcess,
    RunningManifestHandoffRecoveryProcess,
    RunningManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorControlArtifactConflict,
    ManifestHandoffSupervisorReleaseTokenDocument,
    PublishManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    InspectManifestHandoffSupervisorContainer,
    ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorEngineProfile,
    ManifestHandoffSupervisorEngineState,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    CommitManifestHandoffSupervisorGateRelease,
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
    RecordManifestHandoffSupervisorGated,
    RecordManifestHandoffSupervisorRunning,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BoundManifestHandoffSupervisorRuntime,
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorRuntimeConflict,
    RecordManifestHandoffSupervisorReleaseTokenArtifact,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    ManifestHandoffRecoveryServiceResult,
    ManifestHandoffSupervisorGateBindingConflict,
    ManifestHandoffSupervisorServiceConflict,
    ManifestHandoffWriterServiceResult,
    PrepareManifestHandoffRecoveryService,
    PrepareManifestHandoffWriterService,
    ReleaseManifestHandoffSupervisorService,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_CONFLICTS = (
    ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorRuntimeConflict,
    ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorGateBindingConflict,
    ManifestHandoffSupervisorControlArtifactConflict,
)


class ObservationOnlyManifestHandoffSupervisorPrepareCompletion:
    """Observe direct Ready after a separately completed launch/start prefix."""

    __slots__ = ("_engine", "_gates", "_journal", "_recorder", "_runtime")

    def __init__(self, *, journal, runtime_bindings, gate_bindings, engine,
                 wrapper_artifact_recorder) -> None:
        values = (journal, runtime_bindings, gate_bindings, engine,
                  wrapper_artifact_recorder)
        if any(value is None for value in values):
            raise ManifestHandoffRegistryUnavailable
        self._journal, self._runtime, self._gates, self._engine, self._recorder = values

    def __repr__(self) -> str:
        return "ObservationOnlyManifestHandoffSupervisorPrepareCompletion()"

    def prepare_writer(self, command):
        if type(command) is not PrepareManifestHandoffWriterService:
            raise ManifestHandoffRegistryUnavailable
        return self._prepare(command, ManifestHandoffSupervisorEngineProfile.WRITER,
            self._journal.inspect_writer_journal, self._journal.record_writer_gated,
            ManifestHandoffWriterJournalView, PreparedManifestHandoffWriterProcess,
            ManifestHandoffWriterServiceResult)

    def prepare_recovery(self, command):
        if type(command) is not PrepareManifestHandoffRecoveryService:
            raise ManifestHandoffRegistryUnavailable
        return self._prepare(command, ManifestHandoffSupervisorEngineProfile.RECOVERY,
            self._journal.inspect_recovery_journal, self._journal.record_recovery_gated,
            ManifestHandoffRecoveryJournalView, PreparedManifestHandoffRecoveryProcess,
            ManifestHandoffRecoveryServiceResult)

    def _prepare(self, command, profile, inspect_journal, record_gated,
                 view_type, process_type, result_type):
        try:
            journal = inspect_journal(command.registration.handle_id)
            if journal is None:
                return None
            if type(journal) is not view_type or journal.registration != command.registration:
                raise ManifestHandoffRegistryUnavailable
            if journal.state not in {
                ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED,
                ManifestHandoffSupervisorJournalState.PREPARED_GATED,
            }:
                return ManifestHandoffSupervisorServiceConflict()
            runtime = self._runtime.resolve_runtime(command.registration.handle_id)
            gate = self._gates.resolve_gate(command.registration.handle_id)
            if not self._bindings(command, runtime, gate, profile):
                return ManifestHandoffSupervisorServiceConflict()
            observation = self._engine.inspect(
                InspectManifestHandoffSupervisorContainer(runtime.runtime_container_id)
            )
            if (type(observation) in _CONFLICTS or observation is None
                    or observation.runtime_container_id != runtime.runtime_container_id
                    or observation.creation_id != runtime.creation_id
                    or observation.image_digest != runtime.image_digest
                    or observation.launch_document_id != command.launch_document_id
                    or observation.launch_document_digest != command.launch_document_digest
                    or observation.profile is not profile
                    or observation.state is not ManifestHandoffSupervisorEngineState.RUNNING):
                return ManifestHandoffSupervisorServiceConflict()
            ready = self._recorder.record_ready(gate)
            if ready is None:
                return None
            if type(ready) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            if type(ready) is not RecordedManifestHandoffSupervisorControlArtifact:
                raise ManifestHandoffRegistryUnavailable
            if journal.state is ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED:
                journal = record_gated(RecordManifestHandoffSupervisorGated(
                    gate.gated_observation_id, gate.handle_id
                ))
                if journal is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(journal) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
            if (type(journal) is not view_type
                    or journal.state is not ManifestHandoffSupervisorJournalState.PREPARED_GATED):
                raise ManifestHandoffRegistryUnavailable
            request = command.registration.process_request
            return result_type(journal, runtime, process_type(
                gate.handle_id, request.claim_id, request.owner_id, journal.observed_at
            ))
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _bindings(command, runtime, gate, profile):
        return (type(runtime) is BoundManifestHandoffSupervisorRuntime
                and gate == command.gate_binding
                and runtime.handle_id == gate.handle_id == command.registration.handle_id
                and runtime.creation_id == command.creation_id
                and runtime.control_directory_id == gate.control_directory_id
                and runtime.image_digest == command.image_digest
                and gate.profile is profile)


class ObservationOnlyManifestHandoffSupervisorReleaseService:
    """Publish only Release; observe direct child Consumed before Running."""

    __slots__ = ("_artifacts", "_codec", "_engine", "_gates", "_journal",
                 "_publisher", "_recorder", "_runtime")

    def __init__(self, *, journal, runtime_bindings, control_artifacts,
                 gate_bindings, engine, codec, publisher,
                 wrapper_artifact_recorder) -> None:
        values = (journal, runtime_bindings, control_artifacts, gate_bindings,
                  engine, codec, publisher, wrapper_artifact_recorder)
        if any(value is None for value in values):
            raise ManifestHandoffRegistryUnavailable
        (self._journal, self._runtime, self._artifacts, self._gates,
         self._engine, self._codec, self._publisher, self._recorder) = values

    def __repr__(self) -> str:
        return "ObservationOnlyManifestHandoffSupervisorReleaseService()"

    def release_writer(self, command):
        return self._entry(command, ManifestHandoffSupervisorEngineProfile.WRITER,
            self._journal.inspect_writer_journal, self._journal.commit_writer_release,
            self._journal.record_writer_running, ManifestHandoffWriterJournalView,
            RunningManifestHandoffWriterProcess, ManifestHandoffWriterServiceResult)

    def release_recovery(self, command):
        return self._entry(command, ManifestHandoffSupervisorEngineProfile.RECOVERY,
            self._journal.inspect_recovery_journal, self._journal.commit_recovery_release,
            self._journal.record_recovery_running, ManifestHandoffRecoveryJournalView,
            RunningManifestHandoffRecoveryProcess, ManifestHandoffRecoveryServiceResult)

    def _entry(self, command, *arguments):
        if type(command) is not ReleaseManifestHandoffSupervisorService:
            raise ManifestHandoffRegistryUnavailable
        return self._release(command, *arguments)

    def _release(self, command, profile, inspect_journal, commit_release,
                 record_running, view_type, process_type, result_type):
        try:
            journal = inspect_journal(command.handle_id)
            if journal is None:
                return None
            if type(journal) is not view_type:
                raise ManifestHandoffRegistryUnavailable
            if journal.state not in {
                ManifestHandoffSupervisorJournalState.PREPARED_GATED,
                ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED,
                ManifestHandoffSupervisorJournalState.RUNNING,
            } or (journal.release_id is not None
                  and journal.release_id != command.release_id):
                return ManifestHandoffSupervisorServiceConflict()
            runtime = self._runtime.resolve_runtime(command.handle_id)
            gate = self._gates.resolve_gate(command.handle_id)
            if not self._bindings(runtime, gate, journal, profile):
                return ManifestHandoffSupervisorServiceConflict()
            if journal.state is ManifestHandoffSupervisorJournalState.PREPARED_GATED:
                journal = commit_release(CommitManifestHandoffSupervisorGateRelease(
                    command.release_id, command.handle_id
                ))
                if journal is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(journal) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
            if journal.release_id != command.release_id:
                return ManifestHandoffSupervisorServiceConflict()
            token = self._ensure_token(command, gate)
            if type(token) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            consumed = self._recorder.record_consumed(gate, command.release_id)
            if consumed is None:
                return None
            if type(consumed) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            observation = self._engine.inspect(
                InspectManifestHandoffSupervisorContainer(runtime.runtime_container_id)
            )
            if (observation is None or type(observation) in _CONFLICTS
                    or observation.runtime_container_id != runtime.runtime_container_id
                    or observation.creation_id != runtime.creation_id
                    or observation.image_digest != runtime.image_digest
                    or observation.profile is not profile
                    or observation.state is not ManifestHandoffSupervisorEngineState.RUNNING):
                return ManifestHandoffSupervisorServiceConflict()
            if journal.state is not ManifestHandoffSupervisorJournalState.RUNNING:
                journal = record_running(RecordManifestHandoffSupervisorRunning(
                    command.running_observation_id, command.handle_id
                ))
                if journal is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(journal) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
            if type(journal) is not view_type:
                raise ManifestHandoffRegistryUnavailable
            request = journal.registration.process_request
            return result_type(journal, runtime, process_type(
                command.handle_id, request.claim_id, request.owner_id, journal.observed_at
            ))
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _ensure_token(self, command, gate):
        current = self._artifacts.resolve_artifact_role(
            command.handle_id, ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN
        )
        if current is not None:
            if (type(current) is not RecordedManifestHandoffSupervisorControlArtifact
                    or current.artifact_id != command.token_artifact_id
                    or current.correlation_id != command.release_id):
                return ManifestHandoffSupervisorRuntimeConflict()
            return current
        encoded = self._codec.encode(ManifestHandoffSupervisorReleaseTokenDocument(
            command.token_artifact_id, command.handle_id, command.release_id
        ))
        published = self._publisher.publish(PublishManifestHandoffSupervisorControlArtifact(
            gate.control_directory_id, encoded
        ))
        if type(published) is ManifestHandoffSupervisorControlArtifactConflict:
            return published
        result = self._artifacts.record_release_token(
            RecordManifestHandoffSupervisorReleaseTokenArtifact(
                command.token_artifact_id, command.handle_id,
                command.release_id, published.facts
            )
        )
        if result is None:
            raise ManifestHandoffRegistryUnavailable
        return result

    @staticmethod
    def _bindings(runtime, gate, journal, profile):
        return (type(runtime) is BoundManifestHandoffSupervisorRuntime
                and gate is not None
                and runtime.handle_id == gate.handle_id == journal.registration.handle_id
                and runtime.control_directory_id == gate.control_directory_id
                and gate.profile is profile)
