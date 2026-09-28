"""Closed documents and file primitives for supervisor control artifacts."""

from dataclasses import dataclass, field
import hashlib

from .manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
    ManifestHandoffSupervisorHandleId,
)
from .manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId,
    ManifestHandoffSupervisorTerminalObservationId,
)
from .manifest_handoff_supervisor_journal import ManifestHandoffSupervisorGatedObservationId
from .manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactFacts,
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorControlDirectoryId,
)


MAX_MANIFEST_HANDOFF_SUPERVISOR_CONTROL_ARTIFACT_BYTES = 65_536


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorReadyDocument:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    correlation_id: ManifestHandoffSupervisorGatedObservationId = field(repr=False)
    role: ManifestHandoffSupervisorControlArtifactRole = field(
        default=ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY, init=False)

    def __post_init__(self) -> None:
        _validate_document(self, ManifestHandoffSupervisorGatedObservationId)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorReleaseTokenDocument:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    correlation_id: ManifestHandoffSupervisorReleaseId = field(repr=False)
    role: ManifestHandoffSupervisorControlArtifactRole = field(
        default=ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN, init=False)

    def __post_init__(self) -> None:
        _validate_document(self, ManifestHandoffSupervisorReleaseId)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorReleaseConsumedDocument:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    correlation_id: ManifestHandoffSupervisorReleaseId = field(repr=False)
    role: ManifestHandoffSupervisorControlArtifactRole = field(
        default=ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED, init=False)

    def __post_init__(self) -> None:
        _validate_document(self, ManifestHandoffSupervisorReleaseId)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorTerminalEnvelopeDocument:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    correlation_id: ManifestHandoffSupervisorTerminalObservationId = field(repr=False)
    outcome: CompletedManifestHandoffWriterProcess | CompletedManifestHandoffRecoveryProcess = field(repr=False)
    role: ManifestHandoffSupervisorControlArtifactRole = field(
        default=ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE, init=False)

    def __post_init__(self) -> None:
        _validate_document(self, ManifestHandoffSupervisorTerminalObservationId)
        if type(self.outcome) not in (
            CompletedManifestHandoffWriterProcess,
            CompletedManifestHandoffRecoveryProcess,
        ) or self.outcome.handle_id != self.handle_id:
            raise ValueError("manifest handoff supervisor terminal envelope is invalid")


def _validate_document(value: object, correlation_type: type) -> None:
    if not all((
        type(value.artifact_id) is ManifestHandoffSupervisorControlArtifactId,
        type(value.handle_id) is ManifestHandoffSupervisorHandleId,
        type(value.correlation_id) is correlation_type,
        type(value.role) is ManifestHandoffSupervisorControlArtifactRole,
    )):
        raise ValueError("manifest handoff supervisor control document is invalid")


ManifestHandoffSupervisorControlDocument = (
    ManifestHandoffSupervisorReadyDocument
    | ManifestHandoffSupervisorReleaseTokenDocument
    | ManifestHandoffSupervisorReleaseConsumedDocument
    | ManifestHandoffSupervisorTerminalEnvelopeDocument
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlArtifactBytes:
    value: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if (type(self.value) is not bytes or not self.value
                or len(self.value) > MAX_MANIFEST_HANDOFF_SUPERVISOR_CONTROL_ARTIFACT_BYTES):
            raise ValueError("manifest handoff supervisor control artifact bytes are invalid")


@dataclass(frozen=True, slots=True)
class EncodedManifestHandoffSupervisorControlArtifact:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    role: ManifestHandoffSupervisorControlArtifactRole
    content: ManifestHandoffSupervisorControlArtifactBytes = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.artifact_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.role) is ManifestHandoffSupervisorControlArtifactRole,
            type(self.content) is ManifestHandoffSupervisorControlArtifactBytes,
            type(self.facts) is ManifestHandoffSupervisorControlArtifactFacts,
            self.facts.byte_count == len(self.content.value),
            self.facts.sha256 == hashlib.sha256(self.content.value).hexdigest(),
        )):
            raise ValueError("manifest handoff supervisor encoded artifact is invalid")


@dataclass(frozen=True, slots=True)
class PublishManifestHandoffSupervisorControlArtifact:
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    artifact: EncodedManifestHandoffSupervisorControlArtifact = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.control_directory_id) is ManifestHandoffSupervisorControlDirectoryId,
            type(self.artifact) is EncodedManifestHandoffSupervisorControlArtifact,
        )):
            raise ValueError("manifest handoff supervisor publish request is invalid")


@dataclass(frozen=True, slots=True)
class ReadManifestHandoffSupervisorControlArtifact:
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    role: ManifestHandoffSupervisorControlArtifactRole

    def __post_init__(self) -> None:
        if not all((
            type(self.control_directory_id) is ManifestHandoffSupervisorControlDirectoryId,
            type(self.role) is ManifestHandoffSupervisorControlArtifactRole,
        )):
            raise ValueError("manifest handoff supervisor read request is invalid")


@dataclass(frozen=True, slots=True)
class PublishedManifestHandoffSupervisorControlArtifact:
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    role: ManifestHandoffSupervisorControlArtifactRole
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.control_directory_id) is ManifestHandoffSupervisorControlDirectoryId,
            type(self.artifact_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.role) is ManifestHandoffSupervisorControlArtifactRole,
            type(self.facts) is ManifestHandoffSupervisorControlArtifactFacts,
        )):
            raise ValueError("manifest handoff supervisor published artifact is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlArtifactConflict:
    """Detail-free divergent immutable role content."""
