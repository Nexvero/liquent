"""Closed platform facts for persistent supervisor correlations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .manifest_handoff import (
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryOwnerId,
)
from .manifest_handoff_supervisor import ManifestHandoffSupervisorHandleId


def _require_id(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _require_utc(value: object, name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{name} must be an aware UTC datetime")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{name} must be an aware UTC datetime")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorBackendInstanceId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor backend instance id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorPrepareId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor prepare id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorReleaseId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor release id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorTerminateId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor terminate id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorTerminalObservationId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor terminal observation id")


class ManifestHandoffSupervisorBackendStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorBackend:
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId = field(repr=False)
    status: ManifestHandoffSupervisorBackendStatus
    provisioned_at: datetime

    def __post_init__(self) -> None:
        if type(self.backend_instance_id) is not ManifestHandoffSupervisorBackendInstanceId:
            raise ValueError("manifest handoff supervisor backend is invalid")
        if type(self.status) is not ManifestHandoffSupervisorBackendStatus:
            raise ValueError("manifest handoff supervisor backend status is invalid")
        _require_utc(self.provisioned_at, "manifest handoff supervisor provision time")


@dataclass(frozen=True, slots=True)
class ReserveManifestHandoffWriterPreparation:
    prepare_id: ManifestHandoffSupervisorPrepareId = field(repr=False)
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId = field(repr=False)
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    owner_id: ManifestHandoffExecutionOwnerId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.prepare_id) is ManifestHandoffSupervisorPrepareId,
            type(self.backend_instance_id) is ManifestHandoffSupervisorBackendInstanceId,
            type(self.claim_id) is ManifestHandoffExecutionClaimId,
            type(self.owner_id) is ManifestHandoffExecutionOwnerId,
        )):
            raise ValueError("manifest handoff writer preparation request is invalid")


@dataclass(frozen=True, slots=True)
class ReserveManifestHandoffRecoveryPreparation:
    prepare_id: ManifestHandoffSupervisorPrepareId = field(repr=False)
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId = field(repr=False)
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    owner_id: ManifestHandoffRecoveryOwnerId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.prepare_id) is ManifestHandoffSupervisorPrepareId,
            type(self.backend_instance_id) is ManifestHandoffSupervisorBackendInstanceId,
            type(self.claim_id) is ManifestHandoffRecoveryClaimId,
            type(self.owner_id) is ManifestHandoffRecoveryOwnerId,
        )):
            raise ValueError("manifest handoff recovery preparation request is invalid")


@dataclass(frozen=True, slots=True)
class ReservedManifestHandoffWriterPreparation:
    prepare_id: ManifestHandoffSupervisorPrepareId = field(repr=False)
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId = field(repr=False)
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    owner_id: ManifestHandoffExecutionOwnerId = field(repr=False)
    reserved_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.prepare_id) is ManifestHandoffSupervisorPrepareId,
            type(self.backend_instance_id) is ManifestHandoffSupervisorBackendInstanceId,
            type(self.claim_id) is ManifestHandoffExecutionClaimId,
            type(self.owner_id) is ManifestHandoffExecutionOwnerId,
        )):
            raise ValueError("manifest handoff writer preparation is invalid")
        _require_utc(self.reserved_at, "manifest handoff writer preparation time")


@dataclass(frozen=True, slots=True)
class ReservedManifestHandoffRecoveryPreparation:
    prepare_id: ManifestHandoffSupervisorPrepareId = field(repr=False)
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId = field(repr=False)
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    owner_id: ManifestHandoffRecoveryOwnerId = field(repr=False)
    reserved_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.prepare_id) is ManifestHandoffSupervisorPrepareId,
            type(self.backend_instance_id) is ManifestHandoffSupervisorBackendInstanceId,
            type(self.claim_id) is ManifestHandoffRecoveryClaimId,
            type(self.owner_id) is ManifestHandoffRecoveryOwnerId,
        )):
            raise ValueError("manifest handoff recovery preparation is invalid")
        _require_utc(self.reserved_at, "manifest handoff recovery preparation time")


@dataclass(frozen=True, slots=True)
class BindManifestHandoffSupervisorHandle:
    prepare_id: ManifestHandoffSupervisorPrepareId = field(repr=False)
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.prepare_id) is ManifestHandoffSupervisorPrepareId,
            type(self.backend_instance_id) is ManifestHandoffSupervisorBackendInstanceId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
        )):
            raise ValueError("manifest handoff supervisor handle request is invalid")


@dataclass(frozen=True, slots=True)
class BoundManifestHandoffSupervisorHandle:
    prepare_id: ManifestHandoffSupervisorPrepareId = field(repr=False)
    backend_instance_id: ManifestHandoffSupervisorBackendInstanceId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    bound_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.prepare_id) is ManifestHandoffSupervisorPrepareId,
            type(self.backend_instance_id) is ManifestHandoffSupervisorBackendInstanceId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
        )):
            raise ValueError("manifest handoff supervisor handle binding is invalid")
        _require_utc(self.bound_at, "manifest handoff supervisor handle binding time")


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffSupervisorRelease:
    release_id: ManifestHandoffSupervisorReleaseId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.release_id) is ManifestHandoffSupervisorReleaseId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
        )):
            raise ValueError("manifest handoff supervisor release request is invalid")


@dataclass(frozen=True, slots=True)
class RecordedManifestHandoffSupervisorRelease:
    release_id: ManifestHandoffSupervisorReleaseId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    requested_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.release_id) is ManifestHandoffSupervisorReleaseId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
        )):
            raise ValueError("manifest handoff supervisor release is invalid")
        _require_utc(self.requested_at, "manifest handoff supervisor release time")


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffSupervisorTermination:
    terminate_id: ManifestHandoffSupervisorTerminateId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.terminate_id) is ManifestHandoffSupervisorTerminateId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
        )):
            raise ValueError("manifest handoff supervisor termination request is invalid")


@dataclass(frozen=True, slots=True)
class RecordedManifestHandoffSupervisorTermination:
    terminate_id: ManifestHandoffSupervisorTerminateId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    requested_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.terminate_id) is ManifestHandoffSupervisorTerminateId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
        )):
            raise ValueError("manifest handoff supervisor termination is invalid")
        _require_utc(self.requested_at, "manifest handoff supervisor termination time")


@dataclass(frozen=True, slots=True)
class RecordManifestHandoffSupervisorTerminalObservation:
    terminal_observation_id: ManifestHandoffSupervisorTerminalObservationId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.terminal_observation_id) is ManifestHandoffSupervisorTerminalObservationId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
        )):
            raise ValueError("manifest handoff supervisor terminal observation request is invalid")


@dataclass(frozen=True, slots=True)
class RecordedManifestHandoffSupervisorTerminalObservation:
    terminal_observation_id: ManifestHandoffSupervisorTerminalObservationId = field(repr=False)
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    observed_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.terminal_observation_id) is ManifestHandoffSupervisorTerminalObservationId,
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
        )):
            raise ValueError("manifest handoff supervisor terminal observation is invalid")
        _require_utc(self.observed_at, "manifest handoff supervisor terminal observation time")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCorrelationConflict:
    """Detail-free divergent persistent correlation."""
