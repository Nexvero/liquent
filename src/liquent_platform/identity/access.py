"""Stable identity and access vocabulary for the first research slice."""

from enum import Enum
from typing import NewType


UserId = NewType("UserId", str)


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Permission(str, Enum):
    RESEARCH_READ = "research:read"
    RESEARCH_WRITE = "research:write"
