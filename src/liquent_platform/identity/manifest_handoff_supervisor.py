"""Closed values for supervised manifest writer and recovery processes."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .manifest_handoff import (
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffFacts,
    ManifestHandoffName,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryOwnerId,
    ManifestHandoffScopeBinding,
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
class ManifestHandoffSupervisorHandleId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor handle id")


@dataclass(frozen=True, slots=True)
class ManifestHandoffWriterSupervisorRequest:
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    owner_id: ManifestHandoffExecutionOwnerId = field(repr=False)
    binding: ManifestHandoffScopeBinding = field(repr=False)
    handoff_name: ManifestHandoffName

    def __post_init__(self) -> None:
        if not all((
            type(self.claim_id) is ManifestHandoffExecutionClaimId,
            type(self.owner_id) is ManifestHandoffExecutionOwnerId,
            type(self.binding) is ManifestHandoffScopeBinding,
            type(self.handoff_name) is ManifestHandoffName,
        )):
            raise ValueError("manifest handoff writer supervisor request is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffRecoverySupervisorRequest:
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    owner_id: ManifestHandoffRecoveryOwnerId = field(repr=False)
    binding: ManifestHandoffScopeBinding = field(repr=False)
    handoff_name: ManifestHandoffName

    def __post_init__(self) -> None:
        if not all((
            type(self.claim_id) is ManifestHandoffRecoveryClaimId,
            type(self.owner_id) is ManifestHandoffRecoveryOwnerId,
            type(self.binding) is ManifestHandoffScopeBinding,
            type(self.handoff_name) is ManifestHandoffName,
        )):
            raise ValueError("manifest handoff recovery supervisor request is invalid")


@dataclass(frozen=True, slots=True)
class PreparedManifestHandoffWriterProcess:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    owner_id: ManifestHandoffExecutionOwnerId = field(repr=False)
    prepared_at: datetime
    gate_released: bool = field(default=False, init=False)
    writer_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.claim_id) is ManifestHandoffExecutionClaimId,
            type(self.owner_id) is ManifestHandoffExecutionOwnerId,
        )):
            raise ValueError("manifest handoff prepared writer process is invalid")
        _require_utc(self.prepared_at, "manifest handoff writer prepare time")


@dataclass(frozen=True, slots=True)
class RunningManifestHandoffWriterProcess:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    owner_id: ManifestHandoffExecutionOwnerId = field(repr=False)
    released_at: datetime
    gate_released: bool = field(default=True, init=False)
    terminal: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.claim_id) is ManifestHandoffExecutionClaimId,
            type(self.owner_id) is ManifestHandoffExecutionOwnerId,
        )):
            raise ValueError("manifest handoff running writer process is invalid")
        _require_utc(self.released_at, "manifest handoff writer release time")


class ManifestHandoffWriterProcessKind(str, Enum):
    MANIFEST_HANDED_OFF = "manifest_handed_off"
    TARGET_NOT_ABSENT = "target_not_absent"
    SOURCE_NOT_STABLE = "source_not_stable"
    OUTCOME_UNKNOWN = "outcome_unknown"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class CompletedManifestHandoffWriterProcess:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    claim_id: ManifestHandoffExecutionClaimId = field(repr=False)
    owner_id: ManifestHandoffExecutionOwnerId = field(repr=False)
    kind: ManifestHandoffWriterProcessKind
    ended_at: datetime
    filename: str | None = None
    facts: ManifestHandoffFacts | None = field(default=None, repr=False)
    terminal: bool = field(default=True, init=False)
    commit_authorized: bool = field(default=False, init=False)
    staging_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.claim_id) is ManifestHandoffExecutionClaimId,
            type(self.owner_id) is ManifestHandoffExecutionOwnerId,
            type(self.kind) is ManifestHandoffWriterProcessKind,
        )):
            raise ValueError("manifest handoff writer process kind is invalid")
        _require_utc(self.ended_at, "manifest handoff writer end time")
        success = self.kind is ManifestHandoffWriterProcessKind.MANIFEST_HANDED_OFF
        if success != (type(self.facts) is ManifestHandoffFacts):
            raise ValueError("manifest handoff writer process facts are inconsistent")
        if success:
            if (
                type(self.filename) is not str
                or not self.filename
                or "/" in self.filename
                or "\\" in self.filename
                or not self.filename.endswith(".json")
            ):
                raise ValueError("manifest handoff writer filename is invalid")
            try:
                ManifestHandoffName(self.filename[:-5])
            except ValueError:
                raise ValueError("manifest handoff writer filename is invalid") from None
        elif self.filename is not None:
            raise ValueError("manifest handoff writer filename is unexpected")


@dataclass(frozen=True, slots=True)
class PreparedManifestHandoffRecoveryProcess:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    owner_id: ManifestHandoffRecoveryOwnerId = field(repr=False)
    prepared_at: datetime
    gate_released: bool = field(default=False, init=False)
    writer_authorized: bool = field(default=False, init=False)
    cleanup_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.claim_id) is ManifestHandoffRecoveryClaimId,
            type(self.owner_id) is ManifestHandoffRecoveryOwnerId,
        )):
            raise ValueError("manifest handoff prepared recovery process is invalid")
        _require_utc(self.prepared_at, "manifest handoff recovery prepare time")


@dataclass(frozen=True, slots=True)
class RunningManifestHandoffRecoveryProcess:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    owner_id: ManifestHandoffRecoveryOwnerId = field(repr=False)
    released_at: datetime
    gate_released: bool = field(default=True, init=False)
    terminal: bool = field(default=False, init=False)
    writer_authorized: bool = field(default=False, init=False)
    cleanup_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.claim_id) is ManifestHandoffRecoveryClaimId,
            type(self.owner_id) is ManifestHandoffRecoveryOwnerId,
        )):
            raise ValueError("manifest handoff running recovery process is invalid")
        _require_utc(self.released_at, "manifest handoff recovery release time")


class ManifestHandoffRecoveryProcessKind(str, Enum):
    MANIFEST_ABSENT = "manifest_absent"
    MANIFEST_TEMPORARY_ONLY = "manifest_temporary_only"
    MANIFEST_HANDED_OFF = "manifest_handed_off"
    MANIFEST_HANDED_OFF_PENDING_CLEANUP = "manifest_handed_off_pending_cleanup"
    MANIFEST_HANDOFF_CONFLICT = "manifest_handoff_conflict"
    OUTCOME_UNKNOWN = "outcome_unknown"


@dataclass(frozen=True, slots=True)
class CompletedManifestHandoffRecoveryProcess:
    handle_id: ManifestHandoffSupervisorHandleId = field(repr=False)
    claim_id: ManifestHandoffRecoveryClaimId = field(repr=False)
    owner_id: ManifestHandoffRecoveryOwnerId = field(repr=False)
    kind: ManifestHandoffRecoveryProcessKind
    ended_at: datetime
    filename: str | None = None
    facts: ManifestHandoffFacts | None = field(default=None, repr=False)
    terminal: bool = field(default=True, init=False)
    writer_authorized: bool = field(default=False, init=False)
    cleanup_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.handle_id) is ManifestHandoffSupervisorHandleId,
            type(self.claim_id) is ManifestHandoffRecoveryClaimId,
            type(self.owner_id) is ManifestHandoffRecoveryOwnerId,
            type(self.kind) is ManifestHandoffRecoveryProcessKind,
        )):
            raise ValueError("manifest handoff recovery process kind is invalid")
        _require_utc(self.ended_at, "manifest handoff recovery end time")
        factual = self.kind in {
            ManifestHandoffRecoveryProcessKind.MANIFEST_TEMPORARY_ONLY,
            ManifestHandoffRecoveryProcessKind.MANIFEST_HANDED_OFF,
            ManifestHandoffRecoveryProcessKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
        }
        if factual != (type(self.facts) is ManifestHandoffFacts):
            raise ValueError("manifest handoff recovery process facts are inconsistent")
        named = self.kind in {
            ManifestHandoffRecoveryProcessKind.MANIFEST_HANDED_OFF,
            ManifestHandoffRecoveryProcessKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
        }
        if named:
            if (
                type(self.filename) is not str
                or not self.filename
                or "/" in self.filename
                or "\\" in self.filename
                or not self.filename.endswith(".json")
            ):
                raise ValueError("manifest handoff recovery filename is invalid")
            try:
                ManifestHandoffName(self.filename[:-5])
            except ValueError:
                raise ValueError("manifest handoff recovery filename is invalid") from None
        elif self.filename is not None:
            raise ValueError("manifest handoff recovery filename is unexpected")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorConflict:
    """Detail-free divergent process-handle binding."""
