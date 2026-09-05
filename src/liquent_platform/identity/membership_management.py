"""Stable internal identities for managed workspace-membership facts."""

from dataclasses import dataclass, field
from enum import Enum

from liquent_platform.identity.access import UserId
from liquent_platform.identity.access import MembershipStatus, Permission
from liquent_platform.identity.research import WorkspaceId


def _require_identifier(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class WorkspaceMembershipRevisionId:
    """Non-reassignable identity of one complete membership snapshot."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "workspace membership revision id")


@dataclass(frozen=True, slots=True)
class WorkspaceMembershipChangeId:
    """Non-reusable identity of one membership-change decision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "workspace membership change id")


@dataclass(frozen=True, slots=True)
class BootstrappedWorkspaceMembershipManagementAuthority:
    """The initial existing user granted management for one workspace."""

    user_id: UserId
    workspace_id: WorkspaceId

    def __post_init__(self) -> None:
        _require_identifier(self.user_id, "membership authority user id")
        _require_identifier(self.workspace_id, "membership authority workspace id")


@dataclass(frozen=True, slots=True)
class AuthorizedWorkspaceMembershipChange:
    """One committed full membership snapshot and its stable identities."""

    change_id: WorkspaceMembershipChangeId = field(repr=False)
    revision_id: WorkspaceMembershipRevisionId = field(repr=False)
    user_id: UserId
    workspace_id: WorkspaceId
    status: MembershipStatus
    permissions: frozenset[Permission] = field(repr=False)

    def __post_init__(self) -> None:
        if self.status is MembershipStatus.INACTIVE and self.permissions:
            raise ValueError("inactive membership permissions must be empty")


@dataclass(frozen=True, slots=True)
class WorkspaceMembershipAuthoritySetRevisionId:
    """Identity of one immutable complete authority set for one workspace."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "workspace membership authority set revision id")


@dataclass(frozen=True, slots=True)
class WorkspaceMembershipAuthorityLifecycleChangeId:
    """Identity of one regular workspace authority lifecycle decision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "workspace membership authority change id")


@dataclass(frozen=True, slots=True)
class WorkspaceMembershipAuthorityRecoveryId:
    """Identity of one offline workspace authority recovery decision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "workspace membership authority recovery id")


@dataclass(frozen=True, slots=True)
class AnchoredWorkspaceMembershipAuthoritySet:
    """One committed adoption of a workspace's bootstrap authority."""

    change_id: WorkspaceMembershipAuthorityLifecycleChangeId = field(repr=False)
    revision_id: WorkspaceMembershipAuthoritySetRevisionId = field(repr=False)
    workspace_id: WorkspaceId


class WorkspaceMembershipAuthorityLifecycleIntent(str, Enum):
    """The three regular, target-specific workspace authority transitions."""

    GRANT = "grant"
    DEACTIVATE = "deactivate"
    REACTIVATE = "reactivate"


@dataclass(frozen=True, slots=True)
class AuthorizedWorkspaceMembershipAuthorityLifecycleChange:
    """One committed regular workspace authority lifecycle decision."""

    change_id: WorkspaceMembershipAuthorityLifecycleChangeId = field(repr=False)
    revision_id: WorkspaceMembershipAuthoritySetRevisionId = field(repr=False)
    target_user_id: UserId
    workspace_id: WorkspaceId
    intent: WorkspaceMembershipAuthorityLifecycleIntent


@dataclass(frozen=True, slots=True)
class RecoveredWorkspaceMembershipAuthoritySet:
    """One committed offline recovery of historical workspace authority."""

    recovery_id: WorkspaceMembershipAuthorityRecoveryId = field(repr=False)
    revision_id: WorkspaceMembershipAuthoritySetRevisionId = field(repr=False)
    target_user_id: UserId
    workspace_id: WorkspaceId
