"""Parent-owned registration, binding, create, and start prefix without Ready."""

from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    CreateManifestHandoffSupervisorContainer,
    InspectManifestHandoffSupervisorContainer,
    ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorEngineProfile,
    ManifestHandoffSupervisorEngineState,
    StartManifestHandoffSupervisorContainer,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    CommitManifestHandoffSupervisorLaunch,
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    ManifestHandoffSupervisorLaunchDocument,
    ManifestHandoffSupervisorLaunchDocumentConflict,
    PublishManifestHandoffSupervisorLaunchDocument,
    PublishedManifestHandoffSupervisorLaunchDocument,
)
from liquent_platform.identity.manifest_handoff_supervisor_parent_launch import (
    LaunchedManifestHandoffSupervisorParentPrefix,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BindManifestHandoffSupervisorRuntime,
    BoundManifestHandoffSupervisorRuntime,
    ManifestHandoffSupervisorRuntimeConflict,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    ManifestHandoffSupervisorGateBindingConflict,
    ManifestHandoffSupervisorServiceConflict,
    PrepareManifestHandoffRecoveryService,
    PrepareManifestHandoffWriterService,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_CONFLICTS = (
    ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffSupervisorRuntimeConflict,
    ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorGateBindingConflict,
)


class PersistentManifestHandoffSupervisorParentLaunchPrefix:
    """Stop after direct engine Running; never publish or observe Ready."""

    __slots__ = (
        "_engine", "_gates", "_journal", "_launch_codec", "_launch_documents",
        "_runtime",
    )

    def __init__(self, *, journal, runtime_bindings, gate_bindings, engine,
                 launch_documents, launch_document_codec) -> None:
        if any(value is None for value in (
            journal, runtime_bindings, gate_bindings, engine,
            launch_documents, launch_document_codec,
        )):
            raise ManifestHandoffRegistryUnavailable
        self._journal, self._runtime, self._gates, self._engine = (
            journal, runtime_bindings, gate_bindings, engine
        )
        self._launch_documents = launch_documents
        self._launch_codec = launch_document_codec

    def __repr__(self) -> str:
        return "PersistentManifestHandoffSupervisorParentLaunchPrefix()"

    def launch_writer(self, command):
        if type(command) is not PrepareManifestHandoffWriterService:
            raise ManifestHandoffRegistryUnavailable
        return self._launch(command, ManifestHandoffSupervisorEngineProfile.WRITER,
            self._journal.register_writer, self._journal.commit_writer_launch,
            ManifestHandoffWriterJournalView)

    def launch_recovery(self, command):
        if type(command) is not PrepareManifestHandoffRecoveryService:
            raise ManifestHandoffRegistryUnavailable
        return self._launch(command, ManifestHandoffSupervisorEngineProfile.RECOVERY,
            self._journal.register_recovery, self._journal.commit_recovery_launch,
            ManifestHandoffRecoveryJournalView)

    def _launch(self, command, profile, register, commit_launch, view_type):
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
            publication = self._publish_launch_document(command)
            if type(publication) is ManifestHandoffSupervisorLaunchDocumentConflict:
                return ManifestHandoffSupervisorServiceConflict()
            if type(publication) is not PublishedManifestHandoffSupervisorLaunchDocument:
                raise ManifestHandoffRegistryUnavailable
            runtime = self._runtime.resolve_runtime(command.registration.handle_id)
            if runtime is None:
                if journal.state is ManifestHandoffSupervisorJournalState.PREPARED_GATED:
                    raise ManifestHandoffRegistryUnavailable
                runtime = self._create_and_bind(command, profile)
                if runtime is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(runtime) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
            if not self._runtime_matches(runtime, command):
                return ManifestHandoffSupervisorServiceConflict()
            gate = self._gates.bind_gate(command.gate_binding)
            if gate is None:
                raise ManifestHandoffRegistryUnavailable
            if type(gate) in _CONFLICTS or gate != command.gate_binding:
                return ManifestHandoffSupervisorServiceConflict()
            observation = self._engine.inspect(
                InspectManifestHandoffSupervisorContainer(runtime.runtime_container_id)
            )
            if observation is None or type(observation) in _CONFLICTS:
                raise ManifestHandoffRegistryUnavailable
            if not self._observation_matches(observation, runtime, command, profile):
                return ManifestHandoffSupervisorServiceConflict()
            if observation.state is ManifestHandoffSupervisorEngineState.CREATED:
                if journal.state is ManifestHandoffSupervisorJournalState.PREPARED_GATED:
                    return ManifestHandoffSupervisorServiceConflict()
                started = self._engine.start(
                    StartManifestHandoffSupervisorContainer(runtime.runtime_container_id)
                )
                if started is None:
                    raise ManifestHandoffRegistryUnavailable
                if type(started) in _CONFLICTS:
                    return ManifestHandoffSupervisorServiceConflict()
                observation = self._engine.inspect(
                    InspectManifestHandoffSupervisorContainer(runtime.runtime_container_id)
                )
                if (observation is None or type(observation) in _CONFLICTS
                        or not self._observation_matches(
                            observation, runtime, command, profile)):
                    return ManifestHandoffSupervisorServiceConflict()
            if observation.state is not ManifestHandoffSupervisorEngineState.RUNNING:
                return ManifestHandoffSupervisorServiceConflict()
            return LaunchedManifestHandoffSupervisorParentPrefix(
                journal, runtime, gate, observation
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _publish_launch_document(self, command):
        document = ManifestHandoffSupervisorLaunchDocument(
            command.launch_document_id,
            command.creation_id,
            command.gate_binding,
            command.image_digest,
            command.registration.process_request,
        )
        encoded = self._launch_codec.encode(document)
        if encoded.facts.sha256 != command.launch_document_digest.value:
            return ManifestHandoffSupervisorLaunchDocumentConflict()
        published = self._launch_documents.publish(
            PublishManifestHandoffSupervisorLaunchDocument(encoded)
        )
        if type(published) is ManifestHandoffSupervisorLaunchDocumentConflict:
            return published
        if (
            type(published) is not PublishedManifestHandoffSupervisorLaunchDocument
            or published.document_id != command.launch_document_id
            or published.facts != encoded.facts
        ):
            raise ManifestHandoffRegistryUnavailable
        return published

    def _create_and_bind(self, command, profile):
        created = self._engine.create(CreateManifestHandoffSupervisorContainer(
            command.registration.handle_id, command.creation_id,
            command.control_directory_id, command.image_digest,
            command.launch_document_id, command.launch_document_digest, profile,
            command.registration.process_request.binding,
        ))
        if created is None or type(created) in _CONFLICTS:
            return created
        return self._runtime.bind_runtime(BindManifestHandoffSupervisorRuntime(
            created.handle_id, created.creation_id, created.runtime_container_id,
            created.control_directory_id, created.image_digest,
        ))

    @staticmethod
    def _require_journal(journal, view_type, command):
        if type(journal) is not view_type or journal.registration != command.registration:
            raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _runtime_matches(runtime, command):
        return (type(runtime) is BoundManifestHandoffSupervisorRuntime
                and runtime.handle_id == command.registration.handle_id
                and runtime.creation_id == command.creation_id
                and runtime.control_directory_id == command.control_directory_id
                and runtime.image_digest == command.image_digest)

    @staticmethod
    def _observation_matches(observation, runtime, command, profile):
        return (observation.runtime_container_id == runtime.runtime_container_id
                and observation.creation_id == runtime.creation_id
                and observation.image_digest == runtime.image_digest
                and observation.launch_document_id == command.launch_document_id
                and observation.launch_document_digest == command.launch_document_digest
                and observation.profile is profile
                and observation.target_root
                == command.registration.process_request.binding.target_root
                and (profile is ManifestHandoffSupervisorEngineProfile.RECOVERY
                     or observation.source_root
                     == command.registration.process_request.binding.source_root))


class CandidateObservationOnlyManifestHandoffSupervisorPrepareService:
    """Unwired exclusive composition of launch prefix and direct Ready completion."""

    __slots__ = ("_completion", "_launch")

    def __init__(self, *, launch_prefix, prepare_completion) -> None:
        if launch_prefix is None or prepare_completion is None:
            raise ManifestHandoffRegistryUnavailable
        self._launch, self._completion = launch_prefix, prepare_completion

    def __repr__(self) -> str:
        return "CandidateObservationOnlyManifestHandoffSupervisorPrepareService()"

    def prepare_writer(self, command):
        return self._prepare(command, self._launch.launch_writer,
                             self._completion.prepare_writer)

    def prepare_recovery(self, command):
        return self._prepare(command, self._launch.launch_recovery,
                             self._completion.prepare_recovery)

    @staticmethod
    def _prepare(command, launch, complete):
        prefix = launch(command)
        if prefix is None or type(prefix) is ManifestHandoffSupervisorServiceConflict:
            return prefix
        if type(prefix) is not LaunchedManifestHandoffSupervisorParentPrefix:
            raise ManifestHandoffRegistryUnavailable
        return complete(command)
