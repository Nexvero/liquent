"""Persistent identity and onboarding-authority facts."""

from dataclasses import dataclass, field
from enum import Enum

from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import WorkspaceId


class InternalUserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class WorkspaceOnboardingAuthorityStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


def _require_identifier(value: object, field_name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"invalid {field_name}")


def _require_status(value: object, expected: type[Enum], field_name: str) -> None:
    if type(value) is not expected:
        raise ValueError(f"invalid {field_name}")


@dataclass(frozen=True, slots=True)
class InternalUserRecord:
    user_id: UserId = field(repr=False)
    status: InternalUserStatus

    def __post_init__(self) -> None:
        _require_identifier(self.user_id, "user id")
        _require_status(self.status, InternalUserStatus, "user status")


@dataclass(frozen=True, slots=True)
class WorkspaceRecord:
    workspace_id: WorkspaceId = field(repr=False)
    status: WorkspaceStatus

    def __post_init__(self) -> None:
        _require_identifier(self.workspace_id, "workspace id")
        _require_status(self.status, WorkspaceStatus, "workspace status")


@dataclass(frozen=True, slots=True)
class WorkspaceOnboardingAuthorityRecord:
    user_id: UserId = field(repr=False)
    workspace_id: WorkspaceId = field(repr=False)
    status: WorkspaceOnboardingAuthorityStatus

    def __post_init__(self) -> None:
        _require_identifier(self.user_id, "user id")
        _require_identifier(self.workspace_id, "workspace id")
        _require_status(
            self.status,
            WorkspaceOnboardingAuthorityStatus,
            "onboarding authority status",
        )
