from dataclasses import FrozenInstanceError

import pytest

from liquent_platform.identity.access import (
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.research import WorkspaceId


def test_user_id_is_a_distinct_semantic_string_type() -> None:
    assert UserId("user-1") == "user-1"


def test_membership_status_has_only_the_required_states() -> None:
    assert {status.value for status in MembershipStatus} == {"active", "inactive"}


def test_permission_has_only_the_two_research_values() -> None:
    assert {permission.value for permission in Permission} == {
        "research:read",
        "research:write",
    }


def test_workspace_membership_binds_identity_workspace_status_and_permissions() -> None:
    membership = WorkspaceMembership(
        user_id=UserId("user-1"),
        workspace_id=WorkspaceId("workspace-1"),
        status=MembershipStatus.ACTIVE,
        permissions=frozenset({Permission.RESEARCH_READ}),
    )

    assert membership.user_id == "user-1"
    assert membership.workspace_id == "workspace-1"
    assert membership.permissions == frozenset({Permission.RESEARCH_READ})


def test_workspace_membership_is_immutable() -> None:
    membership = WorkspaceMembership(
        user_id=UserId("user-1"),
        workspace_id=WorkspaceId("workspace-1"),
        status=MembershipStatus.ACTIVE,
        permissions=frozenset(),
    )

    with pytest.raises(FrozenInstanceError):
        membership.status = MembershipStatus.INACTIVE  # type: ignore[misc]
