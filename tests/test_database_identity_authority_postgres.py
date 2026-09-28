import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_authority import (
    DatabaseOnboardingManagementAuthority,
)

pytestmark = pytest.mark.postgres_integration


def test_committed_revocation_is_seen_by_a_later_decision(
    postgres_engine: Engine,
) -> None:
    actor = UserId("actor-184")
    target = UserId("target-184")
    workspace = WorkspaceId("workspace-184")
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO identity_users (user_id, status)"
                " VALUES (:actor, 'active'), (:target, 'active')"
            ),
            {"actor": str(actor).encode(), "target": str(target).encode()},
        )
        connection.execute(
            text(
                "INSERT INTO identity_workspaces (workspace_id, status)"
                " VALUES (:workspace, 'active')"
            ),
            {"workspace": str(workspace).encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_onboarding_management"
                " (user_id, workspace_id, status)"
                " VALUES (:actor, :workspace, 'active')"
            ),
            {"actor": str(actor).encode(), "workspace": str(workspace).encode()},
        )

    store = DatabaseOnboardingManagementAuthority(postgres_engine)
    principal = SessionPrincipal(actor)
    assert store.permits_onboarding_management(principal, target, workspace) is True

    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE workspace_onboarding_management SET status='inactive'"
                " WHERE user_id=:actor AND workspace_id=:workspace"
            ),
            {"actor": str(actor).encode(), "workspace": str(workspace).encode()},
        )

    assert store.permits_onboarding_management(principal, target, workspace) is False
