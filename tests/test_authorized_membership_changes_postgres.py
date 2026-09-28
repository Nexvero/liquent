from __future__ import annotations

import threading

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import MembershipStatus, Permission, UserId
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipChangeId,
    WorkspaceMembershipRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.membership_changes import (
    DatabaseAuthorizedWorkspaceMembershipChanges,
)

pytestmark = pytest.mark.postgres_integration


def test_concurrent_exact_change_converges_on_one_revision(
    postgres_engine: Engine, postgres_url: str
) -> None:
    actor = UserId("manager-209-postgres")
    target = UserId("member-209-postgres")
    workspace = WorkspaceId("workspace-209-postgres")
    change = WorkspaceMembershipChangeId("change-209-postgres")
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES"
            " (:actor,'active'),(:target,'active')"
        ), {"actor": actor.encode(), "target": target.encode()})
        connection.execute(text(
            "INSERT INTO identity_workspaces VALUES (:workspace,'active')"
        ), {"workspace": workspace.encode()})
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities"
            " VALUES (:actor,:workspace,'active')"
        ), {"actor": actor.encode(), "workspace": workspace.encode()})
    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(name: str) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseAuthorizedWorkspaceMembershipChanges(
                engine,
                generate_revision_id=lambda: WorkspaceMembershipRevisionId(
                    f"revision-{name}"
                ),
            )
            start.wait(timeout=15)
            outcome: object = store.change_membership(
                change, SessionPrincipal(actor), target, workspace, None,
                MembershipStatus.ACTIVE,
                frozenset({Permission.RESEARCH_WRITE}),
            )
        except Exception as error:
            outcome = error
        finally:
            engine.dispose()
        with guard:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
    assert len({outcome.revision_id for outcome in outcomes}) == 1  # type: ignore[union-attr]
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_revisions"
        )) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM authorized_workspace_membership_changes"
        )) == 1
