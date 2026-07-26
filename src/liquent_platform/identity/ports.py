"""Ports required by the identity and authorization capability."""

from typing import Protocol

from liquent_platform.identity.access import UserId, WorkspaceMembership
from liquent_platform.identity.research import WorkspaceId


class WorkspaceMembershipLookup(Protocol):
    """Find the membership for one user and one workspace."""

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership | None: ...
