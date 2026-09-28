"""Closed commands for cleanup clearance revision mutation and creation."""

from dataclasses import dataclass, field

from .access import UserId
from .manifest_handoff import ManifestHandoffRegistryScopeId
from .manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition,
    ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus,
    ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId,
    ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId,
)
from .manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)


def _require_id(value: object, message: str) -> None:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupManagementChangeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "cleanup management change id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupHoldChangeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "cleanup hold change id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupRecoveryChangeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "cleanup recovery change id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupReferenceChangeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "cleanup reference change id is invalid")


@dataclass(frozen=True, slots=True)
class ChangeManifestHandoffSupervisorControlDirectoryCleanupManagement:
    change_id: ManifestHandoffSupervisorControlDirectoryCleanupManagementChangeId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    expected_revision_id: ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId | None = field(repr=False)
    status: ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus

    def __post_init__(self) -> None:
        if not all((
            type(self.change_id) is ManifestHandoffSupervisorControlDirectoryCleanupManagementChangeId,
            type(self.target_user_id) is str and bool(self.target_user_id),
            type(self.scope_id) is ManifestHandoffRegistryScopeId,
            self.expected_revision_id is None or type(self.expected_revision_id)
            is ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId,
            type(self.status) is ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus,
        )):
            raise ValueError("cleanup management change is invalid")


@dataclass(frozen=True, slots=True)
class ChangeManifestHandoffSupervisorControlDirectoryCleanupHold:
    change_id: ManifestHandoffSupervisorControlDirectoryCleanupHoldChangeId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    expected_revision_id: ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId | None = field(repr=False)
    disposition: ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition

    def __post_init__(self) -> None:
        _validate_target_change(
            self, ManifestHandoffSupervisorControlDirectoryCleanupHoldChangeId,
            ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId)


@dataclass(frozen=True, slots=True)
class ChangeManifestHandoffSupervisorControlDirectoryCleanupRecovery:
    change_id: ManifestHandoffSupervisorControlDirectoryCleanupRecoveryChangeId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    expected_revision_id: ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId | None = field(repr=False)
    disposition: ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition

    def __post_init__(self) -> None:
        _validate_target_change(
            self, ManifestHandoffSupervisorControlDirectoryCleanupRecoveryChangeId,
            ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId)


@dataclass(frozen=True, slots=True)
class ChangeManifestHandoffSupervisorControlDirectoryCleanupReference:
    change_id: ManifestHandoffSupervisorControlDirectoryCleanupReferenceChangeId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    expected_revision_id: ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId | None = field(repr=False)
    disposition: ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition

    def __post_init__(self) -> None:
        _validate_target_change(
            self, ManifestHandoffSupervisorControlDirectoryCleanupReferenceChangeId,
            ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId)


def _validate_target_change(value: object, change_type: type, revision_type: type) -> None:
    if not all((
        type(value.change_id) is change_type,
        type(value.directory_id) is ManifestHandoffSupervisorControlDirectoryId,
        value.expected_revision_id is None
        or type(value.expected_revision_id) is revision_type,
        type(value.disposition)
        is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition,
    )):
        raise ValueError("cleanup target revision change is invalid")


@dataclass(frozen=True, slots=True)
class CommittedManifestHandoffSupervisorControlDirectoryCleanupManagementChange:
    change_id: ManifestHandoffSupervisorControlDirectoryCleanupManagementChangeId = field(repr=False)
    authority: ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.change_id) is ManifestHandoffSupervisorControlDirectoryCleanupManagementChangeId,
            type(self.authority) is ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority,
        )):
            raise ValueError("committed cleanup management change is invalid")


@dataclass(frozen=True, slots=True)
class CommittedManifestHandoffSupervisorControlDirectoryCleanupHoldChange:
    change_id: ManifestHandoffSupervisorControlDirectoryCleanupHoldChangeId = field(repr=False)
    decision: ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision = field(repr=False)

    def __post_init__(self) -> None:
        _validate_committed_target(
            self, ManifestHandoffSupervisorControlDirectoryCleanupHoldChangeId,
            ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision)


@dataclass(frozen=True, slots=True)
class CommittedManifestHandoffSupervisorControlDirectoryCleanupRecoveryChange:
    change_id: ManifestHandoffSupervisorControlDirectoryCleanupRecoveryChangeId = field(repr=False)
    decision: ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision = field(repr=False)

    def __post_init__(self) -> None:
        _validate_committed_target(
            self, ManifestHandoffSupervisorControlDirectoryCleanupRecoveryChangeId,
            ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision)


@dataclass(frozen=True, slots=True)
class CommittedManifestHandoffSupervisorControlDirectoryCleanupReferenceChange:
    change_id: ManifestHandoffSupervisorControlDirectoryCleanupReferenceChangeId = field(repr=False)
    decision: ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision = field(repr=False)

    def __post_init__(self) -> None:
        _validate_committed_target(
            self, ManifestHandoffSupervisorControlDirectoryCleanupReferenceChangeId,
            ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision)


def _validate_committed_target(value: object, change_type: type, decision_type: type) -> None:
    if not all((
        type(value.change_id) is change_type,
        type(value.decision) is decision_type,
    )):
        raise ValueError("committed cleanup target revision change is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict:
    """Detail-free denied, stale, collided, or incompatible mutation."""
