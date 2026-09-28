"""Closed current clearance facts for supervisor control-directory cleanup."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .access import UserId
from .manifest_handoff import ManifestHandoffRegistryScopeId
from .manifest_handoff_supervisor_control_directory import (
    RetiredManifestHandoffSupervisorControlDirectory,
)
from .manifest_handoff_supervisor_control_directory_cleanup import (
    CleanupManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryCleanupDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupDisposition,
)
from .manifest_handoff_supervisor_journal import (
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
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
class ManifestHandoffSupervisorControlDirectoryCleanupClearanceId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory cleanup clearance id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory cleanup management revision id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory cleanup hold revision id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory cleanup recovery revision id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory cleanup reference revision id is invalid")


class ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition(str, Enum):
    CLEAR = "clear"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority:
    revision_id: ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId = field(repr=False)
    actor_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    status: ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus
    resolved_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.revision_id) is ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId,
            type(self.actor_user_id) is str and bool(self.actor_user_id),
            type(self.scope_id) is ManifestHandoffRegistryScopeId,
            type(self.status) is ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus,
        )):
            raise ValueError("manifest handoff supervisor control directory cleanup management authority is invalid")
        _require_utc(self.resolved_at, "manifest handoff supervisor control directory cleanup management authority is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision:
    revision_id: ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId = field(repr=False)
    retired: RetiredManifestHandoffSupervisorControlDirectory = field(repr=False)
    disposition: ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition
    decided_at: datetime

    def __post_init__(self) -> None:
        _validate_target_decision(self, ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision:
    revision_id: ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId = field(repr=False)
    retired: RetiredManifestHandoffSupervisorControlDirectory = field(repr=False)
    disposition: ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition
    decided_at: datetime

    def __post_init__(self) -> None:
        _validate_target_decision(self, ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision:
    revision_id: ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId = field(repr=False)
    retired: RetiredManifestHandoffSupervisorControlDirectory = field(repr=False)
    disposition: ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition
    decided_at: datetime

    def __post_init__(self) -> None:
        _validate_target_decision(self, ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId)


@dataclass(frozen=True, slots=True)
class ClearedManifestHandoffSupervisorControlDirectoryCleanup:
    clearance_id: ManifestHandoffSupervisorControlDirectoryCleanupClearanceId = field(repr=False)
    request: CleanupManifestHandoffSupervisorControlDirectory = field(repr=False)
    retired: RetiredManifestHandoffSupervisorControlDirectory = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    journal: ManifestHandoffWriterJournalView | ManifestHandoffRecoveryJournalView = field(repr=False)
    decision: ManifestHandoffSupervisorControlDirectoryCleanupDecision = field(repr=False)
    management: ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority = field(repr=False)
    hold: ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision = field(repr=False)
    recovery: ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision = field(repr=False)
    references: ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision = field(repr=False)
    cleared_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.clearance_id) is ManifestHandoffSupervisorControlDirectoryCleanupClearanceId,
            type(self.request) is CleanupManifestHandoffSupervisorControlDirectory,
            type(self.retired) is RetiredManifestHandoffSupervisorControlDirectory,
            type(self.scope_id) is ManifestHandoffRegistryScopeId,
            type(self.journal) in (ManifestHandoffWriterJournalView, ManifestHandoffRecoveryJournalView),
            type(self.decision) is ManifestHandoffSupervisorControlDirectoryCleanupDecision,
            type(self.management) is ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority,
            type(self.hold) is ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision,
            type(self.recovery) is ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision,
            type(self.references) is ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision,
        )):
            raise ValueError("manifest handoff supervisor control directory cleanup clearance is invalid")
        _require_utc(self.cleared_at, "manifest handoff supervisor control directory cleanup clearance is invalid")
        if (
            self.journal.state is not ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED
            or self.journal.terminal_observation_id is None
            or self.journal.result is None
        ):
            raise ValueError("manifest handoff supervisor control directory cleanup clearance is invalid")
        if not all((
            self.request.directory_id == self.retired.directory_id,
            self.decision.retired == self.retired,
            self.hold.retired == self.retired,
            self.recovery.retired == self.retired,
            self.references.retired == self.retired,
            self.journal.registration.handle_id == self.retired.handle_id,
            self.journal.result.handle_id == self.retired.handle_id,
            self.journal.registration.process_request.binding.scope_id == self.scope_id,
            self.management.actor_user_id == self.request.actor_user_id,
            self.management.scope_id == self.scope_id,
            self.management.status is ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus.ACTIVE,
            self.decision.disposition is ManifestHandoffSupervisorControlDirectoryCleanupDisposition.ELIGIBLE,
            self.hold.disposition is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR,
            self.recovery.disposition is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR,
            self.references.disposition is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR,
        )):
            raise ValueError("manifest handoff supervisor control directory cleanup clearance is invalid")
        latest_fact = max(
            self.retired.retired_at,
            self.decision.decided_at,
            self.management.resolved_at,
            self.hold.decided_at,
            self.recovery.decided_at,
            self.references.decided_at,
        )
        if self.cleared_at < latest_fact:
            raise ValueError("manifest handoff supervisor control directory cleanup clearance is invalid")


def _validate_target_decision(value: object, revision_type: type) -> None:
    if not all((
        type(value.revision_id) is revision_type,
        type(value.retired) is RetiredManifestHandoffSupervisorControlDirectory,
        type(value.disposition) is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition,
    )):
        raise ValueError("manifest handoff supervisor control directory cleanup clearance decision is invalid")
    _require_utc(value.decided_at, "manifest handoff supervisor control directory cleanup clearance decision is invalid")
    if value.decided_at < value.retired.retired_at:
        raise ValueError("manifest handoff supervisor control directory cleanup clearance decision is invalid")
