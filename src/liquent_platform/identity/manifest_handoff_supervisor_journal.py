"""Closed internal journal values for supervised manifest-handoff jobs."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
    ManifestHandoffRecoverySupervisorRequest,
    ManifestHandoffSupervisorHandleId,
    ManifestHandoffWriterSupervisorRequest,
)
from .manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
    ManifestHandoffSupervisorPrepareId,
    ManifestHandoffSupervisorReleaseId,
    ManifestHandoffSupervisorTerminateId,
    ManifestHandoffSupervisorTerminalObservationId,
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
class ManifestHandoffSupervisorLaunchCommitId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor launch commit id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorGatedObservationId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor gated observation id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorRunningObservationId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor running observation id")


class ManifestHandoffSupervisorJournalState(str, Enum):
    PREPARE_REGISTERED = "prepare_registered"
    LAUNCH_COMMITTED = "launch_committed"
    PREPARED_GATED = "prepared_gated"
    RELEASE_COMMITTED = "release_committed"
    RUNNING = "running"
    TERMINATION_REQUESTED = "termination_requested"
    TERMINAL_OBSERVED = "terminal_observed"


@dataclass(frozen=True, slots=True)
class RegisterManifestHandoffWriterJournalJob:
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId = field(repr=False)
    prepare_id: ManifestHandoffSupervisorPrepareId = field(repr=False)
    launch_commit_id: ManifestHandoffSupervisorLaunchCommitId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    process_request: ManifestHandoffWriterSupervisorRequest = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.backend_instance_id) is ManifestHandoffSupervisorBackendInstanceId,
            type(self.prepare_id) is ManifestHandoffSupervisorPrepareId,
            type(self.launch_commit_id) is ManifestHandoffSupervisorLaunchCommitId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.process_request) is ManifestHandoffWriterSupervisorRequest,
        )):
            raise ValueError("manifest handoff writer journal registration is invalid")


@dataclass(frozen=True, slots=True)
class RegisterManifestHandoffRecoveryJournalJob:
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId = field(repr=False)
    prepare_id: ManifestHandoffSupervisorPrepareId = field(repr=False)
    launch_commit_id: ManifestHandoffSupervisorLaunchCommitId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    process_request: ManifestHandoffRecoverySupervisorRequest = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.backend_instance_id) is ManifestHandoffSupervisorBackendInstanceId,
            type(self.prepare_id) is ManifestHandoffSupervisorPrepareId,
            type(self.launch_commit_id) is ManifestHandoffSupervisorLaunchCommitId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.process_request) is ManifestHandoffRecoverySupervisorRequest,
        )):
            raise ValueError("manifest handoff recovery journal registration is invalid")


@dataclass(frozen=True, slots=True)
class CommitManifestHandoffSupervisorLaunch:
    launch_commit_id: ManifestHandoffSupervisorLaunchCommitId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_transition(self.launch_commit_id, ManifestHandoffSupervisorLaunchCommitId, self.handle_id)


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffSupervisorGated:
    observation_id: ManifestHandoffSupervisorGatedObservationId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_transition(self.observation_id, ManifestHandoffSupervisorGatedObservationId, self.handle_id)


@dataclass(frozen=True, slots=True)
class CommitManifestHandoffSupervisorGateRelease:
    release_id: ManifestHandoffSupervisorReleaseId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_transition(self.release_id, ManifestHandoffSupervisorReleaseId, self.handle_id)


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffSupervisorRunning:
    observation_id: ManifestHandoffSupervisorRunningObservationId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_transition(self.observation_id, ManifestHandoffSupervisorRunningObservationId, self.handle_id)


@dataclass(frozen=True, slots=True)
class RequestManifestHandoffSupervisorTermination:
    terminate_id: ManifestHandoffSupervisorTerminateId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_transition(self.terminate_id, ManifestHandoffSupervisorTerminateId, self.handle_id)


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffWriterJournalTerminal:
    terminal_observation_id: ManifestHandoffSupervisorTerminalObservationId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    result: CompletedManifestHandoffWriterProcess = field(repr=False)

    def __post_init__(self) -> None:
        _validate_terminal(self.terminal_observation_id, self.handle_id, self.result, CompletedManifestHandoffWriterProcess)


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffRecoveryJournalTerminal:
    terminal_observation_id: ManifestHandoffSupervisorTerminalObservationId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    result: CompletedManifestHandoffRecoveryProcess = field(repr=False)

    def __post_init__(self) -> None:
        _validate_terminal(self.terminal_observation_id, self.handle_id, self.result, CompletedManifestHandoffRecoveryProcess)


def _validate_transition(identity: object, identity_type: type, handle: object) -> None:
    if type(identity) is not identity_type or type(handle) is not ManifestHandoffSupervisorHandleId:
        raise ValueError("manifest handoff supervisor journal transition is invalid")


def _validate_terminal(identity: object, handle: object, result: object, result_type: type) -> None:
    _validate_transition(identity, ManifestHandoffSupervisorTerminalObservationId, handle)
    if type(result) is not result_type or result.handle_id != handle:
        raise ValueError("manifest handoff supervisor journal terminal is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffWriterJournalView:
    registration: RegisterManifestHandoffWriterJournalJob = field(repr=False)
    state: ManifestHandoffSupervisorJournalState
    observed_at: datetime
    release_id: ManifestHandoffSupervisorReleaseId | None = field(default=None, repr=False)
    terminate_id: ManifestHandoffSupervisorTerminateId | None = field(default=None, repr=False)
    terminal_observation_id: ManifestHandoffSupervisorTerminalObservationId | None = field(default=None, repr=False)
    result: CompletedManifestHandoffWriterProcess | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _validate_view(self, RegisterManifestHandoffWriterJournalJob, CompletedManifestHandoffWriterProcess)


@dataclass(frozen=True, slots=True)
class ManifestHandoffRecoveryJournalView:
    registration: RegisterManifestHandoffRecoveryJournalJob = field(repr=False)
    state: ManifestHandoffSupervisorJournalState
    observed_at: datetime
    release_id: ManifestHandoffSupervisorReleaseId | None = field(default=None, repr=False)
    terminate_id: ManifestHandoffSupervisorTerminateId | None = field(default=None, repr=False)
    terminal_observation_id: ManifestHandoffSupervisorTerminalObservationId | None = field(default=None, repr=False)
    result: CompletedManifestHandoffRecoveryProcess | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _validate_view(self, RegisterManifestHandoffRecoveryJournalJob, CompletedManifestHandoffRecoveryProcess)


def _validate_view(value: object, registration_type: type, result_type: type) -> None:
    if type(value.registration) is not registration_type:
        raise ValueError("manifest handoff supervisor journal registration is invalid")
    if type(value.state) is not ManifestHandoffSupervisorJournalState:
        raise ValueError("manifest handoff supervisor journal state is invalid")
    _require_utc(value.observed_at, "manifest handoff supervisor journal observation time")
    released = value.state in {
        ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED,
        ManifestHandoffSupervisorJournalState.RUNNING,
    }
    terminal = value.state is ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED
    terminating = value.state is ManifestHandoffSupervisorJournalState.TERMINATION_REQUESTED
    release_present = type(value.release_id) is ManifestHandoffSupervisorReleaseId
    terminate_present = type(value.terminate_id) is ManifestHandoffSupervisorTerminateId
    if value.release_id is not None and not release_present:
        raise ValueError("manifest handoff supervisor journal release is inconsistent")
    if released and not release_present:
        raise ValueError("manifest handoff supervisor journal release is inconsistent")
    if not released and not terminating and not terminal and value.release_id is not None:
        raise ValueError("manifest handoff supervisor journal release is inconsistent")
    if value.terminate_id is not None and not terminate_present:
        raise ValueError("manifest handoff supervisor journal termination is inconsistent")
    if terminating and not terminate_present:
        raise ValueError("manifest handoff supervisor journal termination is inconsistent")
    if not terminating and not terminal and value.terminate_id is not None:
        raise ValueError("manifest handoff supervisor journal termination is inconsistent")
    if terminal != (type(value.terminal_observation_id) is ManifestHandoffSupervisorTerminalObservationId):
        raise ValueError("manifest handoff supervisor terminal identity is inconsistent")
    if terminal != (type(value.result) is result_type):
        raise ValueError("manifest handoff supervisor terminal result is inconsistent")
    if terminal and value.result.handle_id != value.registration.handle_id:
        raise ValueError("manifest handoff supervisor terminal handle is inconsistent")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorJournalConflict:
    """Detail-free divergent journal transition."""
