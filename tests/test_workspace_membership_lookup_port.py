from liquent_platform.identity.access import (
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.ports import WorkspaceMembershipLookup
from liquent_platform.identity.research import WorkspaceId


class StubMembershipLookup:
    def __init__(self, membership: WorkspaceMembership | None) -> None:
        self.membership = membership
        self.requested: tuple[UserId, WorkspaceId] | None = None

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership | None:
        self.requested = (user_id, workspace_id)
        return self.membership


def _lookup(
    port: WorkspaceMembershipLookup,
    user_id: UserId,
    workspace_id: WorkspaceId,
) -> WorkspaceMembership | None:
    return port.get_membership(user_id, workspace_id)


def test_membership_lookup_uses_user_and_workspace_identity() -> None:
    membership = WorkspaceMembership(
        user_id=UserId("user-1"),
        workspace_id=WorkspaceId("workspace-1"),
        status=MembershipStatus.ACTIVE,
        permissions=frozenset({Permission.RESEARCH_READ}),
    )
    lookup = StubMembershipLookup(membership)

    assert _lookup(lookup, membership.user_id, membership.workspace_id) is membership
    assert lookup.requested == (UserId("user-1"), WorkspaceId("workspace-1"))


def test_missing_membership_is_neutral_none() -> None:
    lookup = StubMembershipLookup(None)

    assert _lookup(lookup, UserId("unknown"), WorkspaceId("workspace-1")) is None
