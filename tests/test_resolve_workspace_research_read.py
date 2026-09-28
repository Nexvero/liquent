import pytest

from liquent_platform.application.resolve_workspace_research_read import (
    permits_workspace_research_read,
    resolve_workspace_research_read,
)
from liquent_platform.identity.access import (
    CurrentWorkspaceContext,
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipStoreUnavailable,
)

USER = UserId("user-2658")
WORKSPACE = WorkspaceId("workspace-2658")
PRINCIPAL = SessionPrincipal(USER)
CONTEXT = CurrentWorkspaceContext(USER, WORKSPACE)


class Contexts:
    def __init__(self, result: CurrentWorkspaceContext | None) -> None:
        self.result = result
        self.calls: list[UserId] = []

    def resolve_current_workspace(
        self, user_id: UserId
    ) -> CurrentWorkspaceContext | None:
        self.calls.append(user_id)
        return self.result


class Memberships:
    def __init__(self, result: WorkspaceMembership | None) -> None:
        self.result = result
        self.calls: list[tuple[UserId, WorkspaceId]] = []

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership | None:
        self.calls.append((user_id, workspace_id))
        return self.result


def _membership(
    *permissions: Permission,
    status: MembershipStatus = MembershipStatus.ACTIVE,
    user_id: UserId = USER,
    workspace_id: WorkspaceId = WORKSPACE,
) -> WorkspaceMembership:
    return WorkspaceMembership(
        user_id,
        workspace_id,
        status,
        frozenset(permissions),
    )


@pytest.mark.parametrize(
    "permission", [Permission.RESEARCH_READ, Permission.RESEARCH_WRITE]
)
def test_current_context_requires_fresh_research_read_access(
    permission: Permission,
) -> None:
    contexts = Contexts(CONTEXT)
    memberships = Memberships(_membership(permission))

    assert resolve_workspace_research_read(contexts, memberships, PRINCIPAL) == CONTEXT
    assert contexts.calls == [USER]
    assert memberships.calls == [(USER, WORKSPACE)]


def test_absent_context_stops_before_membership_lookup() -> None:
    contexts = Contexts(None)
    memberships = Memberships(_membership(Permission.RESEARCH_READ))

    assert resolve_workspace_research_read(contexts, memberships, PRINCIPAL) is None
    assert memberships.calls == []


@pytest.mark.parametrize(
    "membership",
    [
        None,
        _membership(),
        _membership(Permission.RESEARCH_READ, status=MembershipStatus.INACTIVE),
        _membership(Permission.RESEARCH_READ, user_id=UserId("other-user")),
        _membership(
            Permission.RESEARCH_READ,
            workspace_id=WorkspaceId("other-workspace"),
        ),
    ],
)
def test_every_membership_denial_is_neutral_none(
    membership: WorkspaceMembership | None,
) -> None:
    assert (
        resolve_workspace_research_read(
            Contexts(CONTEXT), Memberships(membership), PRINCIPAL
        )
        is None
    )


def test_mismatched_context_actor_stops_fail_closed() -> None:
    contexts = Contexts(CurrentWorkspaceContext(UserId("other-user"), WORKSPACE))
    memberships = Memberships(_membership(Permission.RESEARCH_READ))

    assert resolve_workspace_research_read(contexts, memberships, PRINCIPAL) is None
    assert memberships.calls == []


def test_already_resolved_context_can_be_authorized_without_context_lookup() -> None:
    memberships = Memberships(_membership(Permission.RESEARCH_READ))

    assert permits_workspace_research_read(memberships, PRINCIPAL, CONTEXT)
    assert memberships.calls == [(USER, WORKSPACE)]


def test_already_resolved_context_still_binds_the_session_actor() -> None:
    memberships = Memberships(_membership(Permission.RESEARCH_READ))
    mismatched = CurrentWorkspaceContext(UserId("other-user"), WORKSPACE)

    assert not permits_workspace_research_read(memberships, PRINCIPAL, mismatched)
    assert memberships.calls == []


def test_technical_unavailability_is_not_converted_to_denial() -> None:
    class UnavailableContexts:
        def resolve_current_workspace(
            self, user_id: UserId
        ) -> CurrentWorkspaceContext | None:
            raise WorkspaceMembershipStoreUnavailable

    with pytest.raises(WorkspaceMembershipStoreUnavailable):
        resolve_workspace_research_read(
            UnavailableContexts(),
            Memberships(_membership(Permission.RESEARCH_READ)),
            PRINCIPAL,
        )
