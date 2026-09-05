import pytest
from sqlalchemy import Engine, text

from liquent_platform.application.authorize_research import authorize_research
from liquent_platform.identity.access import Permission, UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.workspace_memberships import (
    DatabaseWorkspaceMemberships,
)

pytestmark = pytest.mark.postgres_integration


def test_committed_permission_revocation_is_seen_by_later_decision(
    postgres_engine: Engine,
) -> None:
    user = UserId("user-195")
    workspace = WorkspaceId("workspace-195")
    with postgres_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:user,'active')"),
            {"user": str(user).encode()},
        )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": str(workspace).encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_memberships"
                " (user_id,workspace_id,status) VALUES"
                " (:user,:workspace,'active')"
            ),
            {"user": str(user).encode(), "workspace": str(workspace).encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_membership_permissions VALUES"
                " (:user,:workspace,'research:write')"
            ),
            {"user": str(user).encode(), "workspace": str(workspace).encode()},
        )
    lookup = DatabaseWorkspaceMemberships(postgres_engine)
    principal = SessionPrincipal(user)
    assert authorize_research(
        lookup, principal, workspace, Permission.RESEARCH_WRITE
    ) is True

    with postgres_engine.begin() as connection:
        connection.execute(text("DELETE FROM workspace_membership_permissions"))

    assert authorize_research(
        lookup, principal, workspace, Permission.RESEARCH_WRITE
    ) is False
