"""Closed commands and persistent results for the supervisor service."""

from dataclasses import dataclass, field

from .manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess, CompletedManifestHandoffWriterProcess,
    ManifestHandoffSupervisorHandleId, PreparedManifestHandoffRecoveryProcess,
    PreparedManifestHandoffWriterProcess, RunningManifestHandoffRecoveryProcess,
    RunningManifestHandoffWriterProcess,
)
from .manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId, ManifestHandoffSupervisorTerminateId,
)
from .manifest_handoff_supervisor_engine import ManifestHandoffSupervisorEngineProfile
from .manifest_handoff_supervisor_gate_wrapper import StartManifestHandoffSupervisorGateWrapper
from .manifest_handoff_supervisor_journal import (
    ManifestHandoffRecoveryJournalView, ManifestHandoffSupervisorJournalState,
    ManifestHandoffSupervisorRunningObservationId, ManifestHandoffWriterJournalView,
    RegisterManifestHandoffRecoveryJournalJob, RegisterManifestHandoffWriterJournalJob,
)
from .manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from .manifest_handoff_supervisor_runtime import (
    BoundManifestHandoffSupervisorRuntime, ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId, ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
)


@dataclass(frozen=True, slots=True)
class PrepareManifestHandoffWriterService:
    registration: RegisterManifestHandoffWriterJournalJob = field(repr=False)
    creation_id: ManifestHandoffSupervisorCreationId = field(repr=False)
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)
    launch_document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    launch_document_digest: ManifestHandoffSupervisorLaunchDocumentDigest = field(repr=False)
    gate_binding: StartManifestHandoffSupervisorGateWrapper = field(repr=False)

    def __post_init__(self) -> None:
        _validate_prepare(self, RegisterManifestHandoffWriterJournalJob,
            ManifestHandoffSupervisorEngineProfile.WRITER)


@dataclass(frozen=True, slots=True)
class PrepareManifestHandoffRecoveryService:
    registration: RegisterManifestHandoffRecoveryJournalJob = field(repr=False)
    creation_id: ManifestHandoffSupervisorCreationId = field(repr=False)
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)
    launch_document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    launch_document_digest: ManifestHandoffSupervisorLaunchDocumentDigest = field(repr=False)
    gate_binding: StartManifestHandoffSupervisorGateWrapper = field(repr=False)

    def __post_init__(self) -> None:
        _validate_prepare(self, RegisterManifestHandoffRecoveryJournalJob,
            ManifestHandoffSupervisorEngineProfile.RECOVERY)


def _validate_prepare(value, registration_type, profile) -> None:
    if not all((
        type(value.registration) is registration_type,
        type(value.creation_id) is ManifestHandoffSupervisorCreationId,
        type(value.control_directory_id) is ManifestHandoffSupervisorControlDirectoryId,
        type(value.image_digest) is ManifestHandoffSupervisorImageDigest,
        type(value.launch_document_id) is ManifestHandoffSupervisorControlArtifactId,
        type(value.launch_document_digest) is ManifestHandoffSupervisorLaunchDocumentDigest,
        type(value.gate_binding) is StartManifestHandoffSupervisorGateWrapper,
        value.gate_binding.profile is profile,
        value.gate_binding.handle_id == value.registration.handle_id,
        value.gate_binding.control_directory_id == value.control_directory_id,
    )):
        raise ValueError("manifest handoff supervisor service prepare is invalid")


@dataclass(frozen=True, slots=True)
class ReleaseManifestHandoffSupervisorService:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    release_id: ManifestHandoffSupervisorReleaseId = field(repr=False)
    token_artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    running_observation_id: ManifestHandoffSupervisorRunningObservationId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.release_id) is ManifestHandoffSupervisorReleaseId,
            type(self.token_artifact_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.running_observation_id) is ManifestHandoffSupervisorRunningObservationId,
        )):
            raise ValueError("manifest handoff supervisor service release is invalid")


@dataclass(frozen=True, slots=True)
class TerminateManifestHandoffSupervisorService:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    terminate_id: ManifestHandoffSupervisorTerminateId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.terminate_id) is ManifestHandoffSupervisorTerminateId,
        )):
            raise ValueError("manifest handoff supervisor service termination is invalid")


@dataclass(frozen=True, slots=True)
class InspectManifestHandoffSupervisorService:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.handle_id) is not ManifestHandoffSupervisorHandleId:
            raise ValueError("manifest handoff supervisor service inspection is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffWriterServiceResult:
    journal: ManifestHandoffWriterJournalView = field(repr=False)
    runtime: BoundManifestHandoffSupervisorRuntime = field(repr=False)
    process: PreparedManifestHandoffWriterProcess | RunningManifestHandoffWriterProcess | CompletedManifestHandoffWriterProcess = field(repr=False)

    def __post_init__(self) -> None:
        _validate_result(self, ManifestHandoffWriterJournalView,
            PreparedManifestHandoffWriterProcess, RunningManifestHandoffWriterProcess,
            CompletedManifestHandoffWriterProcess)


@dataclass(frozen=True, slots=True)
class ManifestHandoffRecoveryServiceResult:
    journal: ManifestHandoffRecoveryJournalView = field(repr=False)
    runtime: BoundManifestHandoffSupervisorRuntime = field(repr=False)
    process: PreparedManifestHandoffRecoveryProcess | RunningManifestHandoffRecoveryProcess | CompletedManifestHandoffRecoveryProcess = field(repr=False)

    def __post_init__(self) -> None:
        _validate_result(self, ManifestHandoffRecoveryJournalView,
            PreparedManifestHandoffRecoveryProcess, RunningManifestHandoffRecoveryProcess,
            CompletedManifestHandoffRecoveryProcess)


def _validate_result(value, journal_type, prepared_type, running_type, completed_type) -> None:
    if (type(value.journal) is not journal_type
            or type(value.runtime) is not BoundManifestHandoffSupervisorRuntime
            or value.journal.registration.handle_id != value.runtime.handle_id
            or value.process.handle_id != value.runtime.handle_id):
        raise ValueError("manifest handoff supervisor service result is invalid")
    expected = {
        ManifestHandoffSupervisorJournalState.PREPARED_GATED: prepared_type,
        ManifestHandoffSupervisorJournalState.RUNNING: running_type,
        ManifestHandoffSupervisorJournalState.TERMINATION_REQUESTED: running_type,
        ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED: completed_type,
    }.get(value.journal.state)
    if expected is None or type(value.process) is not expected:
        raise ValueError("manifest handoff supervisor service result is inconsistent")
    if (value.process.claim_id != value.journal.registration.process_request.claim_id
            or value.process.owner_id != value.journal.registration.process_request.owner_id):
        raise ValueError("manifest handoff supervisor service process binding is inconsistent")
    if expected is completed_type and value.journal.result != value.process:
        raise ValueError("manifest handoff supervisor service terminal result is inconsistent")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorServiceConflict:
    """Detail-free cross-system orchestration conflict."""


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorGateBindingConflict:
    """Detail-free divergent immutable gate reservation."""
