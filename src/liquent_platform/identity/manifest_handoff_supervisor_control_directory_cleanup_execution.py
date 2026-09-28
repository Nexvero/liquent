"""Closed physical execution values for supervisor control-directory cleanup."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
    ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome,
    ReconcileManifestHandoffSupervisorControlDirectoryCleanup,
)
from .manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    ManifestHandoffSupervisorControlDirectoryCleanupClearanceId,
)
from .manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)


def _require_id(value: object, message: str) -> None:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(message)


def _require_utc(value: object, message: str) -> None:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() != timezone.utc.utcoffset(value)
    ):
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupPreflightId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory cleanup preflight id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory cleanup write claim id is invalid")


@dataclass(frozen=True, slots=True)
class PreflightManifestHandoffSupervisorControlDirectoryCleanup:
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_attempt_binding(self, "manifest handoff supervisor control directory cleanup preflight is invalid")


@dataclass(frozen=True, slots=True)
class PreparedManifestHandoffSupervisorControlDirectoryCleanup:
    preflight_id: ManifestHandoffSupervisorControlDirectoryCleanupPreflightId = field(repr=False)
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    clearance_id: ManifestHandoffSupervisorControlDirectoryCleanupClearanceId = field(repr=False)
    prepared_at: datetime

    def __post_init__(self) -> None:
        if type(self.preflight_id) is not ManifestHandoffSupervisorControlDirectoryCleanupPreflightId:
            raise ValueError("prepared manifest handoff supervisor control directory cleanup is invalid")
        if type(self.clearance_id) is not ManifestHandoffSupervisorControlDirectoryCleanupClearanceId:
            raise ValueError("prepared manifest handoff supervisor control directory cleanup is invalid")
        _validate_attempt_binding(self, "prepared manifest handoff supervisor control directory cleanup is invalid")
        _require_utc(self.prepared_at, "prepared manifest handoff supervisor control directory cleanup is invalid")


@dataclass(frozen=True, slots=True)
class AbsentManifestHandoffSupervisorControlDirectoryCleanupPreflight:
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    clearance_id: ManifestHandoffSupervisorControlDirectoryCleanupClearanceId = field(repr=False)
    observed_at: datetime

    def __post_init__(self) -> None:
        if type(self.clearance_id) is not ManifestHandoffSupervisorControlDirectoryCleanupClearanceId:
            raise ValueError("absent manifest handoff supervisor control directory cleanup preflight is invalid")
        _validate_attempt_binding(self, "absent manifest handoff supervisor control directory cleanup preflight is invalid")
        _require_utc(self.observed_at, "absent manifest handoff supervisor control directory cleanup preflight is invalid")


@dataclass(frozen=True, slots=True)
class ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup:
    prepared: PreparedManifestHandoffSupervisorControlDirectoryCleanup = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.prepared) is not PreparedManifestHandoffSupervisorControlDirectoryCleanup:
            raise ValueError("manifest handoff supervisor control directory cleanup write claim is invalid")


@dataclass(frozen=True, slots=True)
class ClaimedManifestHandoffSupervisorControlDirectoryCleanup:
    claim_id: ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId = field(repr=False)
    prepared: PreparedManifestHandoffSupervisorControlDirectoryCleanup = field(repr=False)
    claimed_at: datetime

    def __post_init__(self) -> None:
        if type(self.claim_id) is not ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId:
            raise ValueError("claimed manifest handoff supervisor control directory cleanup is invalid")
        if type(self.prepared) is not PreparedManifestHandoffSupervisorControlDirectoryCleanup:
            raise ValueError("claimed manifest handoff supervisor control directory cleanup is invalid")
        _require_utc(self.claimed_at, "claimed manifest handoff supervisor control directory cleanup is invalid")
        if self.claimed_at < self.prepared.prepared_at:
            raise ValueError("claimed manifest handoff supervisor control directory cleanup is invalid")

    @property
    def attempt_id(self):
        return self.prepared.attempt_id

    @property
    def directory_id(self):
        return self.prepared.directory_id


@dataclass(frozen=True, slots=True)
class RemovedManifestHandoffSupervisorControlDirectory:
    claim_id: ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId = field(repr=False)
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    removed_at: datetime

    def __post_init__(self) -> None:
        _validate_claimed_outcome(self, "removed manifest handoff supervisor control directory is invalid")
        _require_utc(self.removed_at, "removed manifest handoff supervisor control directory is invalid")


@dataclass(frozen=True, slots=True)
class UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect:
    claim_id: ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId = field(repr=False)
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_claimed_outcome(self, "unknown manifest handoff supervisor control directory cleanup effect is invalid")


@dataclass(frozen=True, slots=True)
class InspectedManifestHandoffSupervisorControlDirectoryCleanupReconciliation:
    request: ReconcileManifestHandoffSupervisorControlDirectoryCleanup = field(repr=False)
    outcome: ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome
    inspected_at: datetime

    def __post_init__(self) -> None:
        if type(self.request) is not ReconcileManifestHandoffSupervisorControlDirectoryCleanup:
            raise ValueError("inspected manifest handoff supervisor control directory cleanup reconciliation is invalid")
        if type(self.outcome) is not ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome:
            raise ValueError("inspected manifest handoff supervisor control directory cleanup reconciliation is invalid")
        _require_utc(self.inspected_at, "inspected manifest handoff supervisor control directory cleanup reconciliation is invalid")


def _validate_attempt_binding(value: object, message: str) -> None:
    if not all((
        type(value.attempt_id) is ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
        type(value.directory_id) is ManifestHandoffSupervisorControlDirectoryId,
    )):
        raise ValueError(message)


def _validate_claimed_outcome(value: object, message: str) -> None:
    if type(value.claim_id) is not ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId:
        raise ValueError(message)
    _validate_attempt_binding(value, message)
