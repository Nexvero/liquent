"""Restart-safe prepare orchestration for persistent supervisor jobs."""

from liquent_platform.identity.manifest_handoff_supervisor import (
    PreparedManifestHandoffRecoveryProcess,
    PreparedManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    CreateManifestHandoffSupervisorContainer,
    InspectManifestHandoffSupervisorContainer,
    ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorEngineProfile,
    ManifestHandoffSupervisorEngineState,
    StartManifestHandoffSupervisorContainer,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    ManifestHandoffSupervisorGateWrapperConflict,
    ReadyManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    CommitManifestHandoffSupervisorLaunch,
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
    RecordManifestHandoffSupervisorGated,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BindManifestHandoffSupervisorRuntime,
    BoundManifestHandoffSupervisorRuntime,
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorRuntimeConflict,
    RecordManifestHandoffSupervisorReadyArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    ManifestHandoffRecoveryServiceResult,
    ManifestHandoffSupervisorGateBindingConflict,
    ManifestHandoffSupervisorServiceConflict,
    ManifestHandoffWriterServiceResult,
    PrepareManifestHandoffRecoveryService,
    PrepareManifestHandoffWriterService,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_CONFLICTS = (
    ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorRuntimeConflict,
    ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorGateWrapperConflict,
    ManifestHandoffSupervisorGateBindingConflict,
)


class PersistentManifestHandoffSupervisorPrepareService:
    """Advance only the closed prepare prefix of the supervisor workflow."""

    __slots__ = (
        "_journal", "_runtime", "_artifacts", "_gates", "_engine", "_wrapper",
    )

    def __init__(self, *, journal, runtime_bindings, control_artifacts,
                 gate_bindings, engine, gate_wrapper) -> None:
        dependencies = (
            journal, runtime_bindings, control_artifacts, gate_bindings, engine,
            gate_wrapper,
        )
        if any(dependency is None for dependency in dependencies):
            raise ManifestHandoffRegistryUnavailable
        self._journal = journal
        self._runtime = runtime_bindings
        self._artifacts = control_artifacts
        self._gates = gate_bindings
        self._engine = engine
        self._wrapper = gate_wrapper

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorPrepareService()"

    def prepare_writer(self, command):
        if type(command) is not PrepareManifestHandoffWriterService:
            raise ManifestHandoffRegistryUnavailable
        return self._prepare(
            command,
            profile=ManifestHandoffSupervisorEngineProfile.WRITER,
            register=self._journal.register_writer,
            commit_launch=self._journal.commit_writer_launch,
            record_gated=self._journal.record_writer_gated,
            view_type=ManifestHandoffWriterJournalView,
            process_type=PreparedManifestHandoffWriterProcess,
            result_type=ManifestHandoffWriterServiceResult,
        )

    def prepare_recovery(self, command):
        if type(command) is not PrepareManifestHandoffRecoveryService:
            raise ManifestHandoffRegistryUnavailable
        return self._prepare(
            command,
            profile=ManifestHandoffSupervisorEngineProfile.RECOVERY,
            register=self._journal.register_recovery,
            commit_launch=self._journal.commit_recovery_launch,
            record_gated=self._journal.record_recovery_gated,
            view_type=ManifestHandoffRecoveryJournalView,
            process_type=PreparedManifestHandoffRecoveryProcess,
            result_type=ManifestHandoffRecoveryServiceResult,
        )

    def _prepare(self, command, *, profile, register, commit_launch, record_gated,
                 view_type, process_type, result_type):
        try:
            journal = register(command.registration)
            if journal is None:
                return None
            if type(journal) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            self._require_journal(journal, view_type, command)

            if journal.state is ManifestHandoffSupervisorJournalState.PREPARE_REGISTERED:
                journal = commit_launch(CommitManifestHandoffSupervisorLaunch(
                    command.registration.launch_commit_id,
                    command.registration.handle_id,
                ))
                if journal is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(journal) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
                self._require_journal(journal, view_type, command)

            if journal.state not in {
                ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED,
                ManifestHandoffSupervisorJournalState.PREPARED_GATED,
            }:
                return ManifestHandoffSupervisorServiceConflict()

            runtime = self._runtime.resolve_runtime(command.registration.handle_id)
            if runtime is None:
                if journal.state is ManifestHandoffSupervisorJournalState.PREPARED_GATED:
                    raise ManifestHandoffRegistryUnavailable
                runtime = self._create_and_bind(command, profile)
                if type(runtime) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
                if runtime is None:
                    raise ManifestHandoffRegistryUnavailable
            if not self._runtime_matches(runtime, command):
                return ManifestHandoffSupervisorServiceConflict()

            gate = self._gates.bind_gate(command.gate_binding)
            if gate is None:
                raise ManifestHandoffRegistryUnavailable
            if type(gate) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            if gate != command.gate_binding:
                return ManifestHandoffSupervisorServiceConflict()

            observation = self._engine.inspect(
                InspectManifestHandoffSupervisorContainer(runtime.runtime_container_id))
            if observation is None:
                raise ManifestHandoffRegistryUnavailable
            if type(observation) in _CONFLICTS or not self._observed_matches(
                    observation, runtime, profile, command):
                return ManifestHandoffSupervisorServiceConflict()

            if observation.state is ManifestHandoffSupervisorEngineState.CREATED:
                if journal.state is ManifestHandoffSupervisorJournalState.PREPARED_GATED:
                    return ManifestHandoffSupervisorServiceConflict()
                started = self._engine.start(
                    StartManifestHandoffSupervisorContainer(runtime.runtime_container_id))
                if started is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(started) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
                observation = self._engine.inspect(
                    InspectManifestHandoffSupervisorContainer(runtime.runtime_container_id))
                if observation is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(observation) in _CONFLICTS or not self._observed_matches(
                        observation, runtime, profile, command):
                    return ManifestHandoffSupervisorServiceConflict()
            if observation.state is not ManifestHandoffSupervisorEngineState.RUNNING:
                return ManifestHandoffSupervisorServiceConflict()

            ready = self._wrapper.publish_ready(gate)
            if type(ready) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()
            if type(ready) is not ReadyManifestHandoffSupervisorGateWrapper:
                raise ManifestHandoffRegistryUnavailable
            recorded = self._artifacts.record_ready(
                RecordManifestHandoffSupervisorReadyArtifact(
                    gate.ready_artifact_id,
                    gate.handle_id,
                    gate.gated_observation_id,
                    ready.publication.facts,
                ))
            if recorded is None:
                raise ManifestHandoffRegistryUnavailable
            if type(recorded) in _CONFLICTS:
                return ManifestHandoffSupervisorServiceConflict()

            if journal.state is ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED:
                journal = record_gated(RecordManifestHandoffSupervisorGated(
                    gate.gated_observation_id, gate.handle_id))
                if journal is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(journal) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
                self._require_journal(journal, view_type, command)
            if journal.state is not ManifestHandoffSupervisorJournalState.PREPARED_GATED:
                return ManifestHandoffSupervisorServiceConflict()

            process = process_type(
                gate.handle_id,
                command.registration.process_request.claim_id,
                command.registration.process_request.owner_id,
                journal.observed_at,
            )
            return result_type(journal, runtime, process)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _create_and_bind(self, command, profile):
        created = self._engine.create(CreateManifestHandoffSupervisorContainer(
            command.registration.handle_id,
            command.creation_id,
            command.control_directory_id,
            command.image_digest,
            command.launch_document_id,
            command.launch_document_digest,
            profile,
            command.registration.process_request.binding,
        ))
        if created is None or type(created) in _CONFLICTS:
            return created
        return self._runtime.bind_runtime(BindManifestHandoffSupervisorRuntime(
            created.handle_id,
            created.creation_id,
            created.runtime_container_id,
            created.control_directory_id,
            created.image_digest,
        ))

    @staticmethod
    def _require_journal(journal, view_type, command):
        if (type(journal) is not view_type
                or journal.registration != command.registration):
            raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _runtime_matches(runtime, command):
        return (type(runtime) is BoundManifestHandoffSupervisorRuntime
                and runtime.handle_id == command.registration.handle_id
                and runtime.creation_id == command.creation_id
                and runtime.control_directory_id == command.control_directory_id
                and runtime.image_digest == command.image_digest)

    @staticmethod
    def _observed_matches(observation, runtime, profile, command):
        return (observation.runtime_container_id == runtime.runtime_container_id
                and observation.creation_id == runtime.creation_id
                and observation.image_digest == runtime.image_digest
                and observation.launch_document_id == command.launch_document_id
                and observation.launch_document_digest == command.launch_document_digest
                and observation.profile is profile)
