"""Closed immutable job binding consumed by one supervisor wrapper."""

from dataclasses import dataclass, field
import hashlib

from .manifest_handoff_supervisor import (
    ManifestHandoffRecoverySupervisorRequest,
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
    ManifestHandoffSupervisorImageDigest,
    ManifestHandoffSupervisorRuntimeContainerId,
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorJobDocument:
    document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    gate: StartManifestHandoffSupervisorGateWrapper = field(repr=False)
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)
    request: ManifestHandoffWriterSupervisorRequest | ManifestHandoffRecoverySupervisorRequest = field(
        repr=False
    )

    def __post_init__(self) -> None:
        if not all((
            type(self.document_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.gate) is StartManifestHandoffSupervisorGateWrapper,
            type(self.runtime_container_id) is ManifestHandoffSupervisorRuntimeContainerId,
            type(self.image_digest) is ManifestHandoffSupervisorImageDigest,
        )):
            raise ValueError("manifest handoff supervisor job document is invalid")
        expected = (
            ManifestHandoffWriterSupervisorRequest
            if self.gate.profile is ManifestHandoffSupervisorEngineProfile.WRITER
            else ManifestHandoffRecoverySupervisorRequest
        )
        if type(self.request) is not expected:
            raise ValueError("manifest handoff supervisor job document is invalid")


@dataclass(frozen=True, slots=True)
class EncodedManifestHandoffSupervisorJobDocument:
    document: ManifestHandoffSupervisorJobDocument = field(repr=False)
    content: ManifestHandoffSupervisorControlArtifactBytes = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.document) is ManifestHandoffSupervisorJobDocument,
            type(self.content) is ManifestHandoffSupervisorControlArtifactBytes,
            type(self.facts) is ManifestHandoffSupervisorControlArtifactFacts,
            self.facts.byte_count == len(self.content.value),
            self.facts.sha256 == hashlib.sha256(self.content.value).hexdigest(),
        )):
            raise ValueError("manifest handoff supervisor encoded job document is invalid")


@dataclass(frozen=True, slots=True)
class PublishManifestHandoffSupervisorJobDocument:
    document: EncodedManifestHandoffSupervisorJobDocument = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.document) is not EncodedManifestHandoffSupervisorJobDocument:
            raise ValueError("manifest handoff supervisor job publication is invalid")


@dataclass(frozen=True, slots=True)
class PublishedManifestHandoffSupervisorJobDocument:
    document_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.document_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.facts) is ManifestHandoffSupervisorControlArtifactFacts,
        )):
            raise ValueError("manifest handoff supervisor published job document is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorJobDocumentConflict:
    """Detail-free divergent immutable job document."""
