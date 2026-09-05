"""Closed Docker-runtime and private control-artifact correlation values."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re

from .manifest_handoff_supervisor import ManifestHandoffSupervisorHandleId
from .manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId,
    ManifestHandoffSupervisorTerminalObservationId,
)
from .manifest_handoff_supervisor_journal import (
    ManifestHandoffSupervisorGatedObservationId,
)


def _require_id(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _require_utc(value: object, name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{name} must be an aware UTC datetime")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{name} must be an aware UTC datetime")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCreationId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor creation id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorRuntimeContainerId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor runtime container id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlArtifactId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control artifact id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorImageDigest:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", self.value) is None:
            raise ValueError("manifest handoff supervisor image digest is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlArtifactFacts:
    sha256: str = field(repr=False)
    byte_count: int

    def __post_init__(self) -> None:
        if type(self.sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None:
            raise ValueError("manifest handoff supervisor artifact digest is invalid")
        if type(self.byte_count) is not int or self.byte_count < 1:
            raise ValueError("manifest handoff supervisor artifact byte count is invalid")


class ManifestHandoffSupervisorControlArtifactRole(str, Enum):
    WRAPPER_READY = "wrapper_ready"
    RELEASE_TOKEN = "release_token"
    RELEASE_CONSUMED = "release_consumed"
    TERMINAL_ENVELOPE = "terminal_envelope"


@dataclass(frozen=True, slots=True)
class BindManifestHandoffSupervisorRuntime:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    creation_id: ManifestHandoffSupervisorCreationId = field(repr=False)
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)

    def __post_init__(self) -> None:
        _validate_runtime(self)


@dataclass(frozen=True, slots=True)
class BoundManifestHandoffSupervisorRuntime:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    creation_id: ManifestHandoffSupervisorCreationId = field(repr=False)
    runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId = field(repr=False)
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    image_digest: ManifestHandoffSupervisorImageDigest = field(repr=False)
    bound_at: datetime

    def __post_init__(self) -> None:
        _validate_runtime(self)
        _require_utc(self.bound_at, "manifest handoff supervisor runtime binding time")


def _validate_runtime(value: object) -> None:
    if not all((
        type(value.handle_id) is ManifestHandoffSupervisorHandleId,
        type(value.creation_id) is ManifestHandoffSupervisorCreationId,
        type(value.runtime_container_id) is ManifestHandoffSupervisorRuntimeContainerId,
        type(value.control_directory_id) is ManifestHandoffSupervisorControlDirectoryId,
        type(value.image_digest) is ManifestHandoffSupervisorImageDigest,
    )):
        raise ValueError("manifest handoff supervisor runtime binding is invalid")


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffSupervisorReadyArtifact:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    correlation_id: ManifestHandoffSupervisorGatedObservationId = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        _validate_artifact_request(self, ManifestHandoffSupervisorGatedObservationId)


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffSupervisorReleaseTokenArtifact:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    correlation_id: ManifestHandoffSupervisorReleaseId = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        _validate_artifact_request(self, ManifestHandoffSupervisorReleaseId)


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffSupervisorReleaseConsumedArtifact:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    correlation_id: ManifestHandoffSupervisorReleaseId = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        _validate_artifact_request(self, ManifestHandoffSupervisorReleaseId)


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffSupervisorTerminalEnvelopeArtifact:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    correlation_id: ManifestHandoffSupervisorTerminalObservationId = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)

    def __post_init__(self) -> None:
        _validate_artifact_request(self, ManifestHandoffSupervisorTerminalObservationId)


def _validate_artifact_request(value: object, correlation_type: type) -> None:
    if not all((
        type(value.artifact_id) is ManifestHandoffSupervisorControlArtifactId,
        type(value.handle_id) is ManifestHandoffSupervisorHandleId,
        type(value.correlation_id) is correlation_type,
        type(value.facts) is ManifestHandoffSupervisorControlArtifactFacts,
    )):
        raise ValueError("manifest handoff supervisor artifact request is invalid")


@dataclass(frozen=True, slots=True)
class RecordedManifestHandoffSupervisorControlArtifact:
    artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    role: ManifestHandoffSupervisorControlArtifactRole
    correlation_id: ManifestHandoffSupervisorGatedObservationId | ManifestHandoffSupervisorReleaseId | ManifestHandoffSupervisorTerminalObservationId = field(repr=False)
    facts: ManifestHandoffSupervisorControlArtifactFacts = field(repr=False)
    published_at: datetime

    def __post_init__(self) -> None:
        expected = {
            ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY: ManifestHandoffSupervisorGatedObservationId,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN: ManifestHandoffSupervisorReleaseId,
            ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED: ManifestHandoffSupervisorReleaseId,
            ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE: ManifestHandoffSupervisorTerminalObservationId,
        }
        if type(self.role) is not ManifestHandoffSupervisorControlArtifactRole:
            raise ValueError("manifest handoff supervisor artifact role is invalid")
        _validate_artifact_request(self, expected[self.role])
        _require_utc(self.published_at, "manifest handoff supervisor artifact publication time")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorRuntimeConflict:
    """Detail-free divergent runtime or artifact binding."""
