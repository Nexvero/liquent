"""Closed authority-set values for cleanup revision mutation sources."""

from dataclasses import dataclass, field
from enum import Enum

from .access import UserId
from .manifest_handoff import ManifestHandoffRegistryScopeId


def _require_id(value: object, message: str) -> None:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(message)


class ManifestHandoffSupervisorCleanupMutationAuthorityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent(str, Enum):
    GRANT = "grant"
    DEACTIVATE = "deactivate"
    REACTIVATE = "reactivate"


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupMutationAuthorityMember:
    user_id: UserId = field(repr=False)
    status: ManifestHandoffSupervisorCleanupMutationAuthorityStatus

    def __post_init__(self) -> None:
        if (type(self.user_id) is not str or not self.user_id
                or type(self.status) is not ManifestHandoffSupervisorCleanupMutationAuthorityStatus):
            raise ValueError("cleanup mutation authority member is invalid")


@dataclass(frozen=True, slots=True)
class CleanupManagementMutationAuthoritySetRevisionId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup management authority set revision id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupManagementMutationAuthorityLifecycleChangeId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup management authority lifecycle change id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupManagementMutationAuthorityBootstrapId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup management authority bootstrap id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupManagementMutationAuthorityRecoveryId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup management authority recovery id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupHoldMutationAuthoritySetRevisionId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup hold authority set revision id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupHoldMutationAuthorityLifecycleChangeId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup hold authority lifecycle change id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupHoldMutationAuthorityBootstrapId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup hold authority bootstrap id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupHoldMutationAuthorityRecoveryId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup hold authority recovery id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupRecoveryMutationAuthoritySetRevisionId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup recovery authority set revision id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupRecoveryMutationAuthorityLifecycleChangeId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup recovery authority lifecycle change id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupRecoveryMutationAuthorityBootstrapId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup recovery authority bootstrap id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupRecoveryMutationAuthorityRecoveryId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup recovery authority recovery id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupReferenceMutationAuthoritySetRevisionId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup reference authority set revision id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupReferenceMutationAuthorityLifecycleChangeId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup reference authority lifecycle change id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupReferenceMutationAuthorityBootstrapId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup reference authority bootstrap id is invalid")


@dataclass(frozen=True, slots=True)
class CleanupReferenceMutationAuthorityRecoveryId:
    value: str = field(repr=False)
    def __post_init__(self): _require_id(self.value, "cleanup reference authority recovery id is invalid")


def _validate_set(value: object, revision_type: type) -> None:
    if not all((
        type(value.revision_id) is revision_type,
        type(value.scope_id) is ManifestHandoffRegistryScopeId,
        type(value.members) is frozenset and bool(value.members),
        all(type(member) is ManifestHandoffSupervisorCleanupMutationAuthorityMember
            for member in value.members),
        len({member.user_id for member in value.members}) == len(value.members),
        any(member.status is ManifestHandoffSupervisorCleanupMutationAuthorityStatus.ACTIVE
            for member in value.members),
    )):
        raise ValueError("cleanup mutation authority set is invalid")


@dataclass(frozen=True, slots=True)
class CleanupManagementMutationAuthoritySet:
    revision_id: CleanupManagementMutationAuthoritySetRevisionId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    members: frozenset[ManifestHandoffSupervisorCleanupMutationAuthorityMember] = field(repr=False)
    def __post_init__(self): _validate_set(self, CleanupManagementMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class CleanupHoldMutationAuthoritySet:
    revision_id: CleanupHoldMutationAuthoritySetRevisionId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    members: frozenset[ManifestHandoffSupervisorCleanupMutationAuthorityMember] = field(repr=False)
    def __post_init__(self): _validate_set(self, CleanupHoldMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class CleanupRecoveryMutationAuthoritySet:
    revision_id: CleanupRecoveryMutationAuthoritySetRevisionId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    members: frozenset[ManifestHandoffSupervisorCleanupMutationAuthorityMember] = field(repr=False)
    def __post_init__(self): _validate_set(self, CleanupRecoveryMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class CleanupReferenceMutationAuthoritySet:
    revision_id: CleanupReferenceMutationAuthoritySetRevisionId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    members: frozenset[ManifestHandoffSupervisorCleanupMutationAuthorityMember] = field(repr=False)
    def __post_init__(self): _validate_set(self, CleanupReferenceMutationAuthoritySetRevisionId)


def _validate_lifecycle(value: object, change_type: type, revision_type: type) -> None:
    if not all((
        type(value.change_id) is change_type,
        type(value.target_user_id) is str and bool(value.target_user_id),
        type(value.scope_id) is ManifestHandoffRegistryScopeId,
        type(value.expected_revision_id) is revision_type,
        type(value.intent) is ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent,
    )):
        raise ValueError("cleanup mutation authority lifecycle change is invalid")


@dataclass(frozen=True, slots=True)
class ChangeCleanupManagementMutationAuthority:
    change_id: CleanupManagementMutationAuthorityLifecycleChangeId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    expected_revision_id: CleanupManagementMutationAuthoritySetRevisionId = field(repr=False)
    intent: ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent
    def __post_init__(self): _validate_lifecycle(self, CleanupManagementMutationAuthorityLifecycleChangeId, CleanupManagementMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class ChangeCleanupHoldMutationAuthority:
    change_id: CleanupHoldMutationAuthorityLifecycleChangeId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    expected_revision_id: CleanupHoldMutationAuthoritySetRevisionId = field(repr=False)
    intent: ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent
    def __post_init__(self): _validate_lifecycle(self, CleanupHoldMutationAuthorityLifecycleChangeId, CleanupHoldMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class ChangeCleanupRecoveryMutationAuthority:
    change_id: CleanupRecoveryMutationAuthorityLifecycleChangeId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    expected_revision_id: CleanupRecoveryMutationAuthoritySetRevisionId = field(repr=False)
    intent: ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent
    def __post_init__(self): _validate_lifecycle(self, CleanupRecoveryMutationAuthorityLifecycleChangeId, CleanupRecoveryMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class ChangeCleanupReferenceMutationAuthority:
    change_id: CleanupReferenceMutationAuthorityLifecycleChangeId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    expected_revision_id: CleanupReferenceMutationAuthoritySetRevisionId = field(repr=False)
    intent: ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent
    def __post_init__(self): _validate_lifecycle(self, CleanupReferenceMutationAuthorityLifecycleChangeId, CleanupReferenceMutationAuthoritySetRevisionId)


def _validate_bootstrap(value: object, bootstrap_type: type) -> None:
    if not all((
        type(value.bootstrap_id) is bootstrap_type,
        type(value.target_user_id) is str and bool(value.target_user_id),
        type(value.scope_id) is ManifestHandoffRegistryScopeId,
    )):
        raise ValueError("cleanup mutation authority bootstrap is invalid")


@dataclass(frozen=True, slots=True)
class BootstrapCleanupManagementMutationAuthority:
    bootstrap_id: CleanupManagementMutationAuthorityBootstrapId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    def __post_init__(self): _validate_bootstrap(self, CleanupManagementMutationAuthorityBootstrapId)


@dataclass(frozen=True, slots=True)
class BootstrapCleanupHoldMutationAuthority:
    bootstrap_id: CleanupHoldMutationAuthorityBootstrapId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    def __post_init__(self): _validate_bootstrap(self, CleanupHoldMutationAuthorityBootstrapId)


@dataclass(frozen=True, slots=True)
class BootstrapCleanupRecoveryMutationAuthority:
    bootstrap_id: CleanupRecoveryMutationAuthorityBootstrapId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    def __post_init__(self): _validate_bootstrap(self, CleanupRecoveryMutationAuthorityBootstrapId)


@dataclass(frozen=True, slots=True)
class BootstrapCleanupReferenceMutationAuthority:
    bootstrap_id: CleanupReferenceMutationAuthorityBootstrapId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    def __post_init__(self): _validate_bootstrap(self, CleanupReferenceMutationAuthorityBootstrapId)


def _validate_recovery(value: object, recovery_type: type, revision_type: type) -> None:
    if not all((
        type(value.recovery_id) is recovery_type,
        type(value.target_user_id) is str and bool(value.target_user_id),
        type(value.scope_id) is ManifestHandoffRegistryScopeId,
        type(value.expected_revision_id) is revision_type,
    )):
        raise ValueError("cleanup mutation authority recovery is invalid")


@dataclass(frozen=True, slots=True)
class RecoverCleanupManagementMutationAuthority:
    recovery_id: CleanupManagementMutationAuthorityRecoveryId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    expected_revision_id: CleanupManagementMutationAuthoritySetRevisionId = field(repr=False)
    def __post_init__(self): _validate_recovery(self, CleanupManagementMutationAuthorityRecoveryId, CleanupManagementMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class RecoverCleanupHoldMutationAuthority:
    recovery_id: CleanupHoldMutationAuthorityRecoveryId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    expected_revision_id: CleanupHoldMutationAuthoritySetRevisionId = field(repr=False)
    def __post_init__(self): _validate_recovery(self, CleanupHoldMutationAuthorityRecoveryId, CleanupHoldMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class RecoverCleanupRecoveryMutationAuthority:
    recovery_id: CleanupRecoveryMutationAuthorityRecoveryId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    expected_revision_id: CleanupRecoveryMutationAuthoritySetRevisionId = field(repr=False)
    def __post_init__(self): _validate_recovery(self, CleanupRecoveryMutationAuthorityRecoveryId, CleanupRecoveryMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class RecoverCleanupReferenceMutationAuthority:
    recovery_id: CleanupReferenceMutationAuthorityRecoveryId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    scope_id: ManifestHandoffRegistryScopeId = field(repr=False)
    expected_revision_id: CleanupReferenceMutationAuthoritySetRevisionId = field(repr=False)
    def __post_init__(self): _validate_recovery(self, CleanupReferenceMutationAuthorityRecoveryId, CleanupReferenceMutationAuthoritySetRevisionId)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupMutationAuthorityConflict:
    """Detail-free denied, stale, locked-out, or incompatible authority change."""
