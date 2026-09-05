"""Closed engine primitives for manifest handoff supervisor runtimes."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .manifest_handoff import ManifestHandoffScopeBinding
from .manifest_handoff_supervisor import ManifestHandoffSupervisorHandleId
from .manifest_handoff_supervisor_correlation import ManifestHandoffSupervisorTerminateId
from .manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from .manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
    ManifestHandoffSupervisorRuntimeContainerId,
)


class ManifestHandoffSupervisorEngineProfile(str, Enum):
    WRITER = "writer"
    RECOVERY = "recovery"


class ManifestHandoffSupervisorEngineState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    EXITED = "exited"
    DEAD = "dead"


@dataclass(frozen=True, slots=True)
class CreateManifestHandoffSupervisorContainer:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    creation_id: ManifestHandoffSupervisorCreationId = field(repr=False)
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)
    launch_document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    launch_document_digest: ManifestHandoffSupervisorLaunchDocumentDigest = field(repr=False)
    profile: ManifestHandoffSupervisorEngineProfile
    binding: ManifestHandoffScopeBinding = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.creation_id) is ManifestHandoffSupervisorCreationId,
            type(self.control_directory_id) is ManifestHandoffSupervisorControlDirectoryId,
            type(self.image_digest) is ManifestHandoffSupervisorImageDigest,
            type(self.launch_document_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.launch_document_digest) is ManifestHandoffSupervisorLaunchDocumentDigest,
            type(self.profile) is ManifestHandoffSupervisorEngineProfile,
            type(self.binding) is ManifestHandoffScopeBinding,
        )):
            raise ValueError("manifest handoff supervisor engine create request is invalid")


@dataclass(frozen=True, slots=True)
class CreatedManifestHandoffSupervisorContainer:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    creation_id: ManifestHandoffSupervisorCreationId = field(repr=False)
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)
    launch_document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    launch_document_digest: ManifestHandoffSupervisorLaunchDocumentDigest = field(repr=False)
    profile: ManifestHandoffSupervisorEngineProfile
    binding: ManifestHandoffScopeBinding = field(repr=False)

    def __post_init__(self) -> None:
        request = CreateManifestHandoffSupervisorContainer(
            self.handle_id, self.creation_id, self.control_directory_id,
            self.image_digest, self.launch_document_id,
            self.launch_document_digest, self.profile, self.binding,
        )
        if type(self.runtime_container_id) is not ManifestHandoffSupervisorRuntimeContainerId:
            raise ValueError("manifest handoff supervisor created container is invalid")
        del request


@dataclass(frozen=True, slots=True)
class InspectManifestHandoffSupervisorContainer:
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.runtime_container_id) is not ManifestHandoffSupervisorRuntimeContainerId:
            raise ValueError("manifest handoff supervisor inspect request is invalid")


@dataclass(frozen=True, slots=True)
class ObservedManifestHandoffSupervisorContainer:
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)
    creation_id: ManifestHandoffSupervisorCreationId = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)
    launch_document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    launch_document_digest: ManifestHandoffSupervisorLaunchDocumentDigest = field(repr=False)
    profile: ManifestHandoffSupervisorEngineProfile
    state: ManifestHandoffSupervisorEngineState
    source_root: Path | None = field(repr=False)
    target_root: Path = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.runtime_container_id) is ManifestHandoffSupervisorRuntimeContainerId,
            type(self.creation_id) is ManifestHandoffSupervisorCreationId,
            type(self.image_digest) is ManifestHandoffSupervisorImageDigest,
            type(self.launch_document_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.launch_document_digest) is ManifestHandoffSupervisorLaunchDocumentDigest,
            type(self.profile) is ManifestHandoffSupervisorEngineProfile,
            type(self.state) is ManifestHandoffSupervisorEngineState,
            self.source_root is None or (
                isinstance(self.source_root, Path) and self.source_root.is_absolute()
            ),
            isinstance(self.target_root, Path) and self.target_root.is_absolute(),
            (self.profile is ManifestHandoffSupervisorEngineProfile.WRITER)
            == (self.source_root is not None),
        )):
            raise ValueError("manifest handoff supervisor engine observation is invalid")


@dataclass(frozen=True, slots=True)
class StartManifestHandoffSupervisorContainer:
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.runtime_container_id) is not ManifestHandoffSupervisorRuntimeContainerId:
            raise ValueError("manifest handoff supervisor start request is invalid")


@dataclass(frozen=True, slots=True)
class StartedManifestHandoffSupervisorContainer:
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.runtime_container_id) is not ManifestHandoffSupervisorRuntimeContainerId:
            raise ValueError("manifest handoff supervisor start acknowledgement is invalid")


@dataclass(frozen=True, slots=True)
class WaitManifestHandoffSupervisorContainer:
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.runtime_container_id) is not ManifestHandoffSupervisorRuntimeContainerId:
            raise ValueError("manifest handoff supervisor wait request is invalid")


@dataclass(frozen=True, slots=True)
class TerminateManifestHandoffSupervisorContainer:
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)
    terminate_id: ManifestHandoffSupervisorTerminateId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.runtime_container_id) is ManifestHandoffSupervisorRuntimeContainerId,
            type(self.terminate_id) is ManifestHandoffSupervisorTerminateId,
        )):
            raise ValueError("manifest handoff supervisor terminate request is invalid")


@dataclass(frozen=True, slots=True)
class AcceptedManifestHandoffSupervisorTermination:
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)
    terminate_id: ManifestHandoffSupervisorTerminateId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.runtime_container_id) is ManifestHandoffSupervisorRuntimeContainerId,
            type(self.terminate_id) is ManifestHandoffSupervisorTerminateId,
        )):
            raise ValueError("manifest handoff supervisor termination acknowledgement is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineConflict:
    """Detail-free divergent or unsafe engine inventory."""
