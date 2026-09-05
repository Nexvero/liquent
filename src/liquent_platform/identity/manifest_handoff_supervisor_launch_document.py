"""Closed pre-create launch binding for one supervisor wrapper."""

from dataclasses import dataclass, field
import hashlib

from .manifest_handoff_supervisor import (
    ManifestHandoffRecoverySupervisorRequest,
    ManifestHandoffSupervisorHandleId,
    ManifestHandoffWriterSupervisorRequest,
)
from .manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorControlArtifactBytes,
)
from .manifest_handoff_supervisor_engine import ManifestHandoffSupervisorEngineProfile
from .manifest_handoff_supervisor_gate_wrapper import StartManifestHandoffSupervisorGateWrapper
from .manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactFacts,
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
)
from .manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorLaunchDocument:
    document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    creation_id: ManifestHandoffSupervisorCreationId = field(repr=False)
    gate: StartManifestHandoffSupervisorGateWrapper = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)
    request: ManifestHandoffWriterSupervisorRequest | ManifestHandoffRecoverySupervisorRequest = field(
        repr=False
    )

    def __post_init__(self) -> None:
        if not all((
            type(self.document_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.creation_id) is ManifestHandoffSupervisorCreationId,
            type(self.gate) is StartManifestHandoffSupervisorGateWrapper,
            type(self.image_digest) is ManifestHandoffSupervisorImageDigest,
        )):
            raise ValueError("manifest handoff supervisor launch document is invalid")
        expected = (
            ManifestHandoffWriterSupervisorRequest
            if self.gate.profile is ManifestHandoffSupervisorEngineProfile.WRITER
            else ManifestHandoffRecoverySupervisorRequest
        )
        if type(self.request) is not expected:
            raise ValueError("manifest handoff supervisor launch document is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorLaunchDocumentExpectation:
    document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    digest: ManifestHandoffSupervisorLaunchDocumentDigest = field(repr=False)
    creation_id: ManifestHandoffSupervisorCreationId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)
    profile: ManifestHandoffSupervisorEngineProfile

    def __post_init__(self) -> None:
        if not all((
            type(self.document_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.digest) is ManifestHandoffSupervisorLaunchDocumentDigest,
            type(self.creation_id) is ManifestHandoffSupervisorCreationId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.control_directory_id) is ManifestHandoffSupervisorControlDirectoryId,
            type(self.image_digest) is ManifestHandoffSupervisorImageDigest,
            type(self.profile) is ManifestHandoffSupervisorEngineProfile,
        )):
            raise ValueError("manifest handoff supervisor launch expectation is invalid")


@dataclass(frozen=True, slots=True)
class EncodedManifestHandoffSupervisorLaunchDocument:
    document: ManifestHandoffSupervisorLaunchDocument = field(repr=False)
    content: ManifestHandoffSupervisorControlArtifactBytes = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.document) is ManifestHandoffSupervisorLaunchDocument,
            type(self.content) is ManifestHandoffSupervisorControlArtifactBytes,
            type(self.facts) is ManifestHandoffSupervisorControlArtifactFacts,
            self.facts.byte_count == len(self.content.value),
            self.facts.sha256 == hashlib.sha256(self.content.value).hexdigest(),
        )):
            raise ValueError("manifest handoff supervisor encoded launch document is invalid")


@dataclass(frozen=True, slots=True)
class PublishManifestHandoffSupervisorLaunchDocument:
    document: EncodedManifestHandoffSupervisorLaunchDocument = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.document) is not EncodedManifestHandoffSupervisorLaunchDocument:
            raise ValueError("manifest handoff supervisor launch publication is invalid")


@dataclass(frozen=True, slots=True)
class PublishedManifestHandoffSupervisorLaunchDocument:
    document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.document_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.facts) is ManifestHandoffSupervisorControlArtifactFacts,
        )):
            raise ValueError("manifest handoff supervisor published launch document is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorLaunchDocumentConflict:
    """Detail-free divergent immutable launch document."""
