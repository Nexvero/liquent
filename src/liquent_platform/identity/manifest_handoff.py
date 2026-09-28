"""Closed facts for persistent private manifest-handoff attempts."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import re

from liquent_platform.identity.access import UserId


_NAME_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?")


def _require_id(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _require_utc(value: object, name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{name} must be an aware UTC datetime")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{name} must be an aware UTC datetime")


@dataclass(frozen=True, slots=True)
class ManifestHandoffRegistryScopeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff registry scope id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffAttemptId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff attempt id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffReservationId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff reservation id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffObservationId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff observation id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffName:
    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or not _NAME_RE.fullmatch(self.value):
            raise ValueError("manifest handoff name is invalid")


class ManifestHandoffObservationKind(str, Enum):
    RESERVED = "reserved"
    WRITER_STARTED = "writer_started"
    WRITER_HANDED_OFF = "writer_handed_off"
    WRITER_OUTCOME_UNKNOWN = "writer_outcome_unknown"
    MANIFEST_ABSENT = "manifest_absent"
    MANIFEST_TEMPORARY_ONLY = "manifest_temporary_only"
    MANIFEST_HANDED_OFF = "manifest_handed_off"
    MANIFEST_HANDED_OFF_PENDING_CLEANUP = "manifest_handed_off_pending_cleanup"
    MANIFEST_HANDOFF_CONFLICT = "manifest_handoff_conflict"
    CLEANUP_COMPLETED = "cleanup_completed"
    CLEANUP_OUTCOME_UNKNOWN = "cleanup_outcome_unknown"


@dataclass(frozen=True, slots=True)
class ReservedManifestHandoffAttempt:
    reservation_id: ManifestHandoffReservationId = field(repr=False)
    attempt_id: ManifestHandoffAttemptId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    actor_user_id: UserId = field(repr=False)
    handoff_name: ManifestHandoffName
    reserved_at: datetime

    def __post_init__(self) -> None:
        _require_utc(self.reserved_at, "manifest handoff reservation time")


@dataclass(frozen=True, slots=True)
class ManifestHandoffReservationConflict:
    """Detail-free divergent retry or permanently occupied name."""


@dataclass(frozen=True, slots=True)
class ManifestHandoffFacts:
    manifest_sha256: str = field(repr=False)
    file_count: int

    def __post_init__(self) -> None:
        if (
            type(self.manifest_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", self.manifest_sha256) is None
        ):
            raise ValueError("manifest handoff sha256 is invalid")
        if type(self.file_count) is not int or self.file_count < 1:
            raise ValueError("manifest handoff file count must be positive")


@dataclass(frozen=True, slots=True)
class AppendedManifestHandoffObservation:
    observation_id: ManifestHandoffObservationId = field(repr=False)
    attempt_id: ManifestHandoffAttemptId = field(repr=False)
    sequence_number: int
    kind: ManifestHandoffObservationKind
    observed_at: datetime
    facts: ManifestHandoffFacts | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.sequence_number) is not int or self.sequence_number < 2:
            raise ValueError("appended manifest observation sequence must exceed one")
        if type(self.kind) is not ManifestHandoffObservationKind:
            raise ValueError("manifest handoff observation kind is invalid")
        if self.kind is ManifestHandoffObservationKind.RESERVED:
            raise ValueError("reserved manifest observation is not appendable")
        _require_utc(self.observed_at, "manifest handoff observation time")
        factual = {
            ManifestHandoffObservationKind.WRITER_HANDED_OFF,
            ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY,
            ManifestHandoffObservationKind.MANIFEST_HANDED_OFF,
            ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
            ManifestHandoffObservationKind.CLEANUP_COMPLETED,
        }
        if (self.kind in factual) != (self.facts is not None):
            raise ValueError("manifest handoff observation facts do not match kind")


@dataclass(frozen=True, slots=True)
class ManifestHandoffObservationConflict:
    """Detail-free divergent reuse of one observation identity."""


@dataclass(frozen=True, slots=True)
class ManifestHandoffScopeBinding:
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    source_root: Path = field(repr=False)
    target_root: Path = field(repr=False)

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, Path) and value.is_absolute()
            for value in (self.source_root, self.target_root)
        ):
            raise ValueError("manifest handoff roots must be absolute paths")
        if any(
            ".." in value.parts for value in (self.source_root, self.target_root)
        ):
            raise ValueError("manifest handoff roots must not contain traversal")
        try:
            self.source_root.relative_to(self.target_root)
            overlaps = True
        except ValueError:
            try:
                self.target_root.relative_to(self.source_root)
                overlaps = True
            except ValueError:
                overlaps = False
        if overlaps:
            raise ValueError("manifest handoff roots must be lexically separate")


@dataclass(frozen=True, slots=True)
class ManifestHandoffCompositionRequest:
    reservation_id: ManifestHandoffReservationId = field(repr=False)
    actor_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    handoff_name: ManifestHandoffName

    def __post_init__(self) -> None:
        if type(self.actor_user_id) is not str or not self.actor_user_id:
            raise ValueError("manifest handoff composition actor is invalid")


class ManifestHandoffCompositionKind(str, Enum):
    MANIFEST_HANDED_OFF = "manifest_handed_off"
    RECONCILIATION_REQUIRED = "reconciliation_required"


@dataclass(frozen=True, slots=True)
class ManifestHandoffCompositionResult:
    attempt_id: ManifestHandoffAttemptId = field(repr=False)
    kind: ManifestHandoffCompositionKind
    filename: str | None = None
    facts: ManifestHandoffFacts | None = field(default=None, repr=False)
    staging_authorized: bool = field(default=False, init=False)
    commit_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not ManifestHandoffCompositionKind:
            raise ValueError("manifest handoff composition kind is invalid")
        confirmed = self.kind is ManifestHandoffCompositionKind.MANIFEST_HANDED_OFF
        valid_filename = (
            type(self.filename) is str
            and bool(self.filename)
            and Path(self.filename).name == self.filename
            and self.filename.endswith(".json")
            and _NAME_RE.fullmatch(self.filename[:-5]) is not None
        )
        if confirmed != valid_filename or confirmed != (self.facts is not None):
            raise ValueError("manifest handoff composition result is inconsistent")


@dataclass(frozen=True, slots=True)
class ManifestHandoffCompositionConflict:
    """Detail-free conflict from a controlled composition dependency."""


@dataclass(frozen=True, slots=True)
class ManifestHandoffAttemptView:
    attempt_id: ManifestHandoffAttemptId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    actor_user_id: UserId = field(repr=False)
    handoff_name: ManifestHandoffName
    latest_observation: ManifestHandoffObservationKind
    reserved_at: datetime

    def __post_init__(self) -> None:
        if type(self.latest_observation) is not ManifestHandoffObservationKind:
            raise ValueError("manifest handoff observation kind is invalid")
        _require_utc(self.reserved_at, "manifest handoff reservation time")


@dataclass(frozen=True, slots=True)
class ManifestHandoffExecutionClaimId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff execution claim id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffExecutionOwnerId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff execution owner id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffExecutionEndId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff execution end id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffLeaseRenewalId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff lease renewal id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffRecoveryClaimId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff recovery claim id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffRecoveryOwnerId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff recovery owner id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffRecoveryEndId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff recovery end id")


@dataclass(frozen=True, slots=True)
class ClaimedManifestHandoffExecution:
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    attempt_id: ManifestHandoffAttemptId = field(repr=False)
    owner_id: ManifestHandoffExecutionOwnerId = field(repr=False)
    claimed_at: datetime
    lease_expires_at: datetime
    writer_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _require_utc(self.claimed_at, "manifest handoff execution claim time")
        _require_utc(self.lease_expires_at, "manifest handoff execution lease expiry")
        if self.lease_expires_at <= self.claimed_at:
            raise ValueError("manifest handoff execution lease must be positive")


@dataclass(frozen=True, slots=True)
class RenewedManifestHandoffExecutionLease:
    renewal_id: ManifestHandoffLeaseRenewalId = field(repr=False)
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    owner_id: ManifestHandoffExecutionOwnerId = field(repr=False)
    renewed_at: datetime
    lease_expires_at: datetime
    recovery_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _require_utc(self.renewed_at, "manifest handoff execution renewal time")
        _require_utc(self.lease_expires_at, "manifest handoff execution lease expiry")
        if self.lease_expires_at <= self.renewed_at:
            raise ValueError("manifest handoff execution lease must be positive")


@dataclass(frozen=True, slots=True)
class StartedManifestHandoffExecution:
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    attempt_id: ManifestHandoffAttemptId = field(repr=False)
    observation_id: ManifestHandoffObservationId = field(repr=False)
    owner_id: ManifestHandoffExecutionOwnerId = field(repr=False)
    started_at: datetime

    def __post_init__(self) -> None:
        _require_utc(self.started_at, "manifest handoff execution start time")


class ManifestHandoffExecutionEndKind(str, Enum):
    OUTCOME_SECURED = "outcome_secured"
    OUTCOME_UNKNOWN = "outcome_unknown"
    START_NOT_CONFIRMED = "start_not_confirmed"


@dataclass(frozen=True, slots=True)
class RecordedManifestHandoffExecutionEnd:
    end_id: ManifestHandoffExecutionEndId = field(repr=False)
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    attempt_id: ManifestHandoffAttemptId = field(repr=False)
    kind: ManifestHandoffExecutionEndKind
    ended_at: datetime

    def __post_init__(self) -> None:
        if type(self.kind) is not ManifestHandoffExecutionEndKind:
            raise ValueError("manifest handoff execution end kind is invalid")
        _require_utc(self.ended_at, "manifest handoff execution end time")


class ManifestHandoffRecoveryEndKind(str, Enum):
    OUTCOME_SECURED = "outcome_secured"
    OUTCOME_UNKNOWN = "outcome_unknown"
    START_NOT_CONFIRMED = "start_not_confirmed"


@dataclass(frozen=True, slots=True)
class RecordedManifestHandoffRecoveryEnd:
    end_id: ManifestHandoffRecoveryEndId = field(repr=False)
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    attempt_id: ManifestHandoffAttemptId = field(repr=False)
    kind: ManifestHandoffRecoveryEndKind
    ended_at: datetime

    def __post_init__(self) -> None:
        if type(self.kind) is not ManifestHandoffRecoveryEndKind:
            raise ValueError("manifest handoff recovery end kind is invalid")
        _require_utc(self.ended_at, "manifest handoff recovery end time")


@dataclass(frozen=True, slots=True)
class ManifestHandoffRecoveryRequest:
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    actor_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    handoff_name: ManifestHandoffName
    owner_id: ManifestHandoffRecoveryOwnerId = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.actor_user_id) is not str or not self.actor_user_id:
            raise ValueError("manifest handoff recovery actor is invalid")


@dataclass(frozen=True, slots=True)
class ClaimedManifestHandoffRecovery:
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    attempt_id: ManifestHandoffAttemptId = field(repr=False)
    execution_claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    owner_id: ManifestHandoffRecoveryOwnerId = field(repr=False)
    claimed_at: datetime
    writer_authorized: bool = field(default=False, init=False)
    cleanup_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _require_utc(self.claimed_at, "manifest handoff recovery claim time")


@dataclass(frozen=True, slots=True)
class AppendedManifestHandoffRecoveryObservation:
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    observation: AppendedManifestHandoffObservation

    def __post_init__(self) -> None:
        if type(self.observation) is not AppendedManifestHandoffObservation:
            raise ValueError("manifest handoff recovery observation is invalid")
        if self.observation.kind not in {
            ManifestHandoffObservationKind.MANIFEST_ABSENT,
            ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY,
            ManifestHandoffObservationKind.MANIFEST_HANDED_OFF,
            ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
            ManifestHandoffObservationKind.MANIFEST_HANDOFF_CONFLICT,
        }:
            raise ValueError("manifest handoff recovery observation kind is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffOwnershipConflict:
    """Detail-free divergent reuse of an ownership identity."""
