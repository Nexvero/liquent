"""Closed staged contract for the manifest handoff gate wrapper."""

from dataclasses import dataclass, field

from .manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
    ManifestHandoffSupervisorHandleId,
)
from .manifest_handoff_supervisor_control_artifact import (
    PublishedManifestHandoffSupervisorControlArtifact,
)
from .manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId,
    ManifestHandoffSupervisorTerminalObservationId,
)
from .manifest_handoff_supervisor_engine import ManifestHandoffSupervisorEngineProfile
from .manifest_handoff_supervisor_journal import ManifestHandoffSupervisorGatedObservationId
from .manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorControlDirectoryId,
)


@dataclass(frozen=True, slots=True)
class StartManifestHandoffSupervisorGateWrapper:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    control_directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    profile: ManifestHandoffSupervisorEngineProfile
    ready_artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    gated_observation_id: ManifestHandoffSupervisorGatedObservationId = field(repr=False)
    consumed_artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    terminal_artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    terminal_observation_id: ManifestHandoffSupervisorTerminalObservationId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.control_directory_id) is ManifestHandoffSupervisorControlDirectoryId,
            type(self.profile) is ManifestHandoffSupervisorEngineProfile,
            type(self.ready_artifact_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.gated_observation_id) is ManifestHandoffSupervisorGatedObservationId,
            type(self.consumed_artifact_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.terminal_artifact_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.terminal_observation_id) is ManifestHandoffSupervisorTerminalObservationId,
            len({self.ready_artifact_id, self.consumed_artifact_id, self.terminal_artifact_id}) == 3,
        )):
            raise ValueError("manifest handoff supervisor gate wrapper binding is invalid")


@dataclass(frozen=True, slots=True)
class ReadyManifestHandoffSupervisorGateWrapper:
    binding: StartManifestHandoffSupervisorGateWrapper = field(repr=False)
    publication: PublishedManifestHandoffSupervisorControlArtifact = field(repr=False)

    def __post_init__(self) -> None:
        if (type(self.binding) is not StartManifestHandoffSupervisorGateWrapper
                or not _publication_matches(self.publication, self.binding,
                    self.binding.ready_artifact_id,
                    ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY)):
            raise ValueError("manifest handoff supervisor wrapper ready state is invalid")


@dataclass(frozen=True, slots=True)
class AcceptedManifestHandoffSupervisorReleaseToken:
    ready: ReadyManifestHandoffSupervisorGateWrapper = field(repr=False)
    token_artifact_id: ManifestHandoffSupervisorControlArtifactId = field(repr=False)
    release_id: ManifestHandoffSupervisorReleaseId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.ready) is ReadyManifestHandoffSupervisorGateWrapper,
            type(self.token_artifact_id) is ManifestHandoffSupervisorControlArtifactId,
            type(self.release_id) is ManifestHandoffSupervisorReleaseId,
            self.token_artifact_id not in {
                self.ready.binding.ready_artifact_id,
                self.ready.binding.consumed_artifact_id,
                self.ready.binding.terminal_artifact_id,
            },
        )):
            raise ValueError("manifest handoff supervisor release token is invalid")


@dataclass(frozen=True, slots=True)
class ReleasedManifestHandoffSupervisorGateWrapper:
    token: AcceptedManifestHandoffSupervisorReleaseToken = field(repr=False)
    publication: PublishedManifestHandoffSupervisorControlArtifact = field(repr=False)

    def __post_init__(self) -> None:
        if (type(self.token) is not AcceptedManifestHandoffSupervisorReleaseToken
                or not _publication_matches(self.publication, self.token.ready.binding,
                    self.token.ready.binding.consumed_artifact_id,
                    ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED)):
            raise ValueError("manifest handoff supervisor released wrapper state is invalid")


def _publication_matches(publication, binding, artifact_id, role) -> bool:
    return all((
        type(publication) is PublishedManifestHandoffSupervisorControlArtifact,
        publication.control_directory_id == binding.control_directory_id,
        publication.artifact_id == artifact_id,
        publication.role is role,
    ))


ManifestHandoffSupervisorTerminalGateState = (
    ReadyManifestHandoffSupervisorGateWrapper | ReleasedManifestHandoffSupervisorGateWrapper
)


@dataclass(frozen=True, slots=True)
class CompleteManifestHandoffSupervisorGateWrapper:
    gate: ManifestHandoffSupervisorTerminalGateState = field(repr=False)
    outcome: CompletedManifestHandoffWriterProcess | CompletedManifestHandoffRecoveryProcess = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.gate) is ReadyManifestHandoffSupervisorGateWrapper:
            binding = self.gate.binding
        elif type(self.gate) is ReleasedManifestHandoffSupervisorGateWrapper:
            binding = self.gate.token.ready.binding
        else:
            raise ValueError("manifest handoff supervisor terminal gate state is invalid")
        expected = (CompletedManifestHandoffWriterProcess
            if binding.profile is ManifestHandoffSupervisorEngineProfile.WRITER
            else CompletedManifestHandoffRecoveryProcess)
        if type(self.outcome) is not expected or self.outcome.handle_id != binding.handle_id:
            raise ValueError("manifest handoff supervisor terminal outcome is invalid")


@dataclass(frozen=True, slots=True)
class CompletedManifestHandoffSupervisorGateWrapper:
    request: CompleteManifestHandoffSupervisorGateWrapper = field(repr=False)
    publication: PublishedManifestHandoffSupervisorControlArtifact = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.request) is not CompleteManifestHandoffSupervisorGateWrapper:
            raise ValueError("manifest handoff supervisor completed wrapper is invalid")
        gate = self.request.gate
        binding = gate.binding if type(gate) is ReadyManifestHandoffSupervisorGateWrapper else gate.token.ready.binding
        if not _publication_matches(self.publication, binding, binding.terminal_artifact_id,
                ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE):
            raise ValueError("manifest handoff supervisor terminal publication is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorGateWrapperConflict:
    """Detail-free divergent immutable gate artifact."""
