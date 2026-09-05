import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.membership_management_authority import (
    DatabaseWorkspaceMembershipManagementAuthority,
)

pytestmark = pytest.mark.postgres_integration


def test_committed_membership_management_revocation_is_immediately_visible(
    postgres_engine: Engine,
) -> None:
    actor = UserId("manager-207-postgres")
    workspace = WorkspaceId("workspace-207-postgres")
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES (:actor,'active')"
        ), {"actor": actor.encode()})
        connection.execute(text(
            "INSERT INTO identity_workspaces VALUES (:workspace,'active')"
        ), {"workspace": workspace.encode()})
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities"
            " VALUES (:actor,:workspace,'active')"
        ), {"actor": actor.encode(), "workspace": workspace.encode()})
    lookup = DatabaseWorkspaceMembershipManagementAuthority(postgres_engine)
    assert lookup.permits_workspace_membership_management(
        SessionPrincipal(actor), workspace
    ) is True

    with postgres_engine.begin() as connection:
        connection.execute(text(
            "UPDATE workspace_membership_management_authorities"
            " SET status='inactive'"
        ))

    assert lookup.permits_workspace_membership_management(
        SessionPrincipal(actor), workspace
    ) is False
