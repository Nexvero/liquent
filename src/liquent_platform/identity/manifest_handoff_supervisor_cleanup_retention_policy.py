"""Closed values for supervisor cleanup retention policy administration."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from .access import UserId
from .manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
)
from .manifest_handoff_supervisor_cleanup_retention import (
    ManifestHandoffSupervisorCleanupRetentionDataClass,
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


def _require_duration(value: object, message: str) -> None:
    if (
        type(value) is not timedelta
        or value <= timedelta(0)
        or value.microseconds != 0
    ):
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionPolicyBootstrapId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "cleanup retention policy bootstrap id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionPolicyChangeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "cleanup retention policy change id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "cleanup retention policy authority revision id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityChangeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "cleanup retention policy authority change id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityRecoveryId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "cleanup retention policy authority recovery id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionPolicyRevision:
    revision_id: ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId = field(
        repr=False
    )
    data_class: ManifestHandoffSupervisorCleanupRetentionDataClass
    minimum_retention: timedelta
    created_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.revision_id)
            is ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
            self.data_class
            is ManifestHandoffSupervisorCleanupRetentionDataClass.SUPERVISOR_CONTROL_DIRECTORY,
        )):
            raise ValueError("cleanup retention policy revision is invalid")
        _require_duration(
            self.minimum_retention, "cleanup retention policy revision is invalid"
        )
        _require_utc(self.created_at, "cleanup retention policy revision is invalid")


@dataclass(frozen=True, slots=True)
class ActiveManifestHandoffSupervisorCleanupRetentionPolicy:
    policy: ManifestHandoffSupervisorCleanupRetentionPolicyRevision = field(
        repr=False
    )
    activated_at: datetime

    def __post_init__(self) -> None:
        if type(self.policy) is not ManifestHandoffSupervisorCleanupRetentionPolicyRevision:
            raise ValueError("active cleanup retention policy is invalid")
        _require_utc(self.activated_at, "active cleanup retention policy is invalid")
        if self.activated_at < self.policy.created_at:
            raise ValueError("active cleanup retention policy is invalid")


class ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityIntent(str, Enum):
    GRANT = "grant"
    DEACTIVATE = "deactivate"
    REACTIVATE = "reactivate"


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityMember:
    user_id: UserId = field(repr=False)
    status: ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityStatus

    def __post_init__(self) -> None:
        if not all((
            type(self.user_id) is str and bool(self.user_id),
            type(self.status)
            is ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityStatus,
        )):
            raise ValueError("cleanup retention policy authority member is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet:
    revision_id: ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId = field(
        repr=False
    )
    members: frozenset[
        ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityMember
    ] = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.revision_id)
            is ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId,
            type(self.members) is frozenset and bool(self.members),
            all(
                type(member)
                is ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityMember
                for member in self.members
            ),
            len({member.user_id for member in self.members}) == len(self.members),
            any(
                member.status
                is ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityStatus.ACTIVE
                for member in self.members
            ),
        )):
            raise ValueError("cleanup retention policy authority set is invalid")


@dataclass(frozen=True, slots=True)
class BootstrapManifestHandoffSupervisorCleanupRetentionPolicy:
    bootstrap_id: ManifestHandoffSupervisorCleanupRetentionPolicyBootstrapId = field(
        repr=False
    )
    target_user_id: UserId = field(repr=False)
    minimum_retention: timedelta

    def __post_init__(self) -> None:
        if not all((
            type(self.bootstrap_id)
            is ManifestHandoffSupervisorCleanupRetentionPolicyBootstrapId,
            type(self.target_user_id) is str and bool(self.target_user_id),
        )):
            raise ValueError("cleanup retention policy bootstrap is invalid")
        _require_duration(
            self.minimum_retention, "cleanup retention policy bootstrap is invalid"
        )


@dataclass(frozen=True, slots=True)
class BootstrappedManifestHandoffSupervisorCleanupRetentionPolicy:
    command: BootstrapManifestHandoffSupervisorCleanupRetentionPolicy = field(
        repr=False
    )
    active_policy: ActiveManifestHandoffSupervisorCleanupRetentionPolicy = field(
        repr=False
    )
    authority_set: ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet = field(
        repr=False
    )

    def __post_init__(self) -> None:
        if not all((
            type(self.command)
            is BootstrapManifestHandoffSupervisorCleanupRetentionPolicy,
            type(self.active_policy)
            is ActiveManifestHandoffSupervisorCleanupRetentionPolicy,
            type(self.authority_set)
            is ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet,
            self.active_policy.policy.minimum_retention
            == self.command.minimum_retention,
            any(
                member.user_id == self.command.target_user_id
                and member.status
                is ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityStatus.ACTIVE
                for member in self.authority_set.members
            ),
        )):
            raise ValueError("bootstrapped cleanup retention policy is invalid")

    @property
    def bootstrap_id(self):
        return self.command.bootstrap_id


class ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent(str, Enum):
    REPLACE = "replace"
    DEACTIVATE = "deactivate"


@dataclass(frozen=True, slots=True)
class ChangeManifestHandoffSupervisorCleanupRetentionPolicy:
    change_id: ManifestHandoffSupervisorCleanupRetentionPolicyChangeId = field(
        repr=False
    )
    expected_revision_id: ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId | None = field(
        repr=False
    )
    intent: ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent
    minimum_retention: timedelta | None

    def __post_init__(self) -> None:
        if not all((
            type(self.change_id)
            is ManifestHandoffSupervisorCleanupRetentionPolicyChangeId,
            self.expected_revision_id is None
            or type(self.expected_revision_id)
            is ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
            type(self.intent)
            is ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent,
        )):
            raise ValueError("cleanup retention policy change is invalid")
        if self.intent is ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent.REPLACE:
            _require_duration(
                self.minimum_retention, "cleanup retention policy change is invalid"
            )
        elif self.minimum_retention is not None:
            raise ValueError("cleanup retention policy change is invalid")


@dataclass(frozen=True, slots=True)
class ChangedManifestHandoffSupervisorCleanupRetentionPolicy:
    command: ChangeManifestHandoffSupervisorCleanupRetentionPolicy = field(
        repr=False
    )
    active_policy: ActiveManifestHandoffSupervisorCleanupRetentionPolicy | None = field(
        repr=False
    )

    def __post_init__(self) -> None:
        if not all((
            type(self.command)
            is ChangeManifestHandoffSupervisorCleanupRetentionPolicy,
            self.active_policy is None
            or type(self.active_policy)
            is ActiveManifestHandoffSupervisorCleanupRetentionPolicy,
        )):
            raise ValueError("changed cleanup retention policy is invalid")
        if self.command.intent is ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent.REPLACE:
            if (
                self.active_policy is None
                or self.active_policy.policy.minimum_retention
                != self.command.minimum_retention
                or self.active_policy.policy.revision_id
                == self.command.expected_revision_id
            ):
                raise ValueError("changed cleanup retention policy is invalid")
        elif self.active_policy is not None:
            raise ValueError("changed cleanup retention policy is invalid")

    @property
    def change_id(self):
        return self.command.change_id


@dataclass(frozen=True, slots=True)
class ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority:
    change_id: ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityChangeId = field(
        repr=False
    )
    target_user_id: UserId = field(repr=False)
    expected_revision_id: ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId = field(
        repr=False
    )
    intent: ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityIntent

    def __post_init__(self) -> None:
        if not all((
            type(self.change_id)
            is ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityChangeId,
            type(self.target_user_id) is str and bool(self.target_user_id),
            type(self.expected_revision_id)
            is ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId,
            type(self.intent)
            is ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityIntent,
        )):
            raise ValueError("cleanup retention policy authority change is invalid")


@dataclass(frozen=True, slots=True)
class RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority:
    recovery_id: ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityRecoveryId = field(
        repr=False
    )
    target_user_id: UserId = field(repr=False)
    expected_revision_id: ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId = field(
        repr=False
    )

    def __post_init__(self) -> None:
        if not all((
            type(self.recovery_id)
            is ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityRecoveryId,
            type(self.target_user_id) is str and bool(self.target_user_id),
            type(self.expected_revision_id)
            is ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId,
        )):
            raise ValueError("cleanup retention policy authority recovery is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionPolicyConflict:
    """Detail-free stale, denied, reused, lockout, or incompatible change."""
