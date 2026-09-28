"""Stable identities for persistent user and workspace lifecycle facts."""

from dataclasses import dataclass, field
from enum import Enum

from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import WorkspaceId


def _require_identifier(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class UserLifecycleRevisionId:
    """Identity of one immutable complete user lifecycle snapshot."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "user lifecycle revision id")


@dataclass(frozen=True, slots=True)
class UserLifecycleChangeId:
    """Non-reusable identity of one user lifecycle decision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "user lifecycle change id")


@dataclass(frozen=True, slots=True)
class WorkspaceLifecycleRevisionId:
    """Identity of one immutable complete workspace lifecycle snapshot."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "workspace lifecycle revision id")


@dataclass(frozen=True, slots=True)
class WorkspaceLifecycleChangeId:
    """Non-reusable identity of one workspace lifecycle decision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "workspace lifecycle change id")


@dataclass(frozen=True, slots=True)
class AnchoredIdentityLifecycleFoundation:
    """One controlled adoption of a canonical initial identity inventory."""

    user_id: UserId
    workspace_id: WorkspaceId
    user_revision_id: UserLifecycleRevisionId = field(repr=False)
    workspace_revision_id: WorkspaceLifecycleRevisionId = field(repr=False)


@dataclass(frozen=True, slots=True)
class UserLifecycleAuthoritySetRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "user lifecycle authority revision id")


@dataclass(frozen=True, slots=True)
class UserLifecycleAuthorityChangeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "user lifecycle authority change id")


@dataclass(frozen=True, slots=True)
class WorkspaceLifecycleAuthoritySetRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "workspace lifecycle authority revision id")


@dataclass(frozen=True, slots=True)
class WorkspaceLifecycleAuthorityChangeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "workspace lifecycle authority change id")


class LifecycleAuthorityIntent(str, Enum):
    GRANT = "grant"
    DEACTIVATE = "deactivate"
    REACTIVATE = "reactivate"


@dataclass(frozen=True, slots=True)
class AnchoredUserLifecycleAuthoritySet:
    change_id: UserLifecycleAuthorityChangeId = field(repr=False)
    revision_id: UserLifecycleAuthoritySetRevisionId = field(repr=False)


@dataclass(frozen=True, slots=True)
class AnchoredWorkspaceLifecycleAuthoritySet:
    change_id: WorkspaceLifecycleAuthorityChangeId = field(repr=False)
    revision_id: WorkspaceLifecycleAuthoritySetRevisionId = field(repr=False)


@dataclass(frozen=True, slots=True)
class AuthorizedUserLifecycleAuthorityChange:
    change_id: UserLifecycleAuthorityChangeId = field(repr=False)
    revision_id: UserLifecycleAuthoritySetRevisionId = field(repr=False)
    target_user_id: UserId
    intent: LifecycleAuthorityIntent


@dataclass(frozen=True, slots=True)
class AuthorizedWorkspaceLifecycleAuthorityChange:
    change_id: WorkspaceLifecycleAuthorityChangeId = field(repr=False)
    revision_id: WorkspaceLifecycleAuthoritySetRevisionId = field(repr=False)
    target_user_id: UserId
    intent: LifecycleAuthorityIntent


class UserLifecycleIntent(str, Enum):
    CREATE = "create"
    DEACTIVATE = "deactivate"
    REACTIVATE = "reactivate"


@dataclass(frozen=True, slots=True)
class AuthorizedUserLifecycleChange:
    change_id: UserLifecycleChangeId = field(repr=False)
    revision_id: UserLifecycleRevisionId = field(repr=False)
    target_user_id: UserId
    intent: UserLifecycleIntent


class WorkspaceLifecycleIntent(str, Enum):
    CREATE = "create"
    DEACTIVATE = "deactivate"


@dataclass(frozen=True, slots=True)
class AuthorizedWorkspaceLifecycleChange:
    change_id: WorkspaceLifecycleChangeId = field(repr=False)
    revision_id: WorkspaceLifecycleRevisionId = field(repr=False)
    target_workspace_id: WorkspaceId
    initial_onboarding_manager_user_id: UserId | None
    intent: WorkspaceLifecycleIntent
