from liquent_platform.application.authorize_research import authorize_research
from liquent_platform.identity.access import (
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.research import WorkspaceId


class StubMembershipLookup:
    def __init__(self, result: WorkspaceMembership | None) -> None:
        self.result = result

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership | None:
        return self.result


def _membership(
    *,
    user_id: str = "user-1",
    workspace_id: str = "workspace-1",
    status: MembershipStatus = MembershipStatus.ACTIVE,
    permissions: frozenset[Permission] = frozenset({Permission.RESEARCH_READ}),
) -> WorkspaceMembership:
    return WorkspaceMembership(
        user_id=UserId(user_id),
        workspace_id=WorkspaceId(workspace_id),
        status=status,
        permissions=permissions,
    )


def test_authorization_uses_resolved_membership_and_existing_policy() -> None:
    assert authorize_research(
        StubMembershipLookup(_membership()),
        UserId("user-1"),
        WorkspaceId("workspace-1"),
        Permission.RESEARCH_READ,
    )


def test_missing_membership_is_denied() -> None:
    assert not authorize_research(
        StubMembershipLookup(None),
        UserId("user-1"),
        WorkspaceId("workspace-1"),
        Permission.RESEARCH_READ,
    )


def test_denial_from_existing_policy_is_preserved() -> None:
    assert not authorize_research(
        StubMembershipLookup(_membership()),
        UserId("user-1"),
        WorkspaceId("workspace-1"),
        Permission.RESEARCH_WRITE,
    )


def test_mismatched_membership_identity_is_denied_fail_closed() -> None:
    assert not authorize_research(
        StubMembershipLookup(_membership(user_id="another-user")),
        UserId("user-1"),
        WorkspaceId("workspace-1"),
        Permission.RESEARCH_READ,
    )
    assert not authorize_research(
        StubMembershipLookup(_membership(workspace_id="another-workspace")),
        UserId("user-1"),
        WorkspaceId("workspace-1"),
        Permission.RESEARCH_READ,
    )
