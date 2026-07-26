"""Stable identity and access vocabulary for the first research slice."""

from dataclasses import dataclass
from enum import Enum
from typing import NewType

from liquent_platform.identity.research import WorkspaceId


UserId = NewType("UserId", str)


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Permission(str, Enum):
    RESEARCH_READ = "research:read"
    RESEARCH_WRITE = "research:write"


@dataclass(frozen=True, slots=True)
class WorkspaceMembership:
    user_id: UserId
    workspace_id: WorkspaceId
    status: MembershipStatus
    permissions: frozenset[Permission]
