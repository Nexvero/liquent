from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import CurrentWorkspaceContext, UserId
from liquent_platform.identity.ports import CurrentWorkspaceContextLookup
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipStoreUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.workspace_contexts import (
    DatabaseCurrentWorkspaceContexts,
)

USER = UserId("user-2656")
WORKSPACE = WorkspaceId("workspace-2656")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'contexts.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _add_user(engine: Engine, status: str = "active") -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:user,:status)"),
            {"user": USER.encode(), "status": status},
        )


def _add_workspace_membership(
    engine: Engine,
    workspace: WorkspaceId,
    *,
    workspace_status: str = "active",
    membership_status: str = "active",
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,:status)"),
            {"workspace": workspace.encode(), "status": workspace_status},
        )
        connection.execute(
            text("INSERT INTO workspace_memberships VALUES (:user,:workspace,:status,NULL)"),
            {
                "user": USER.encode(),
                "workspace": workspace.encode(),
                "status": membership_status,
            },
        )


def test_exactly_one_active_context_satisfies_port(engine: Engine) -> None:
    _add_user(engine)
    _add_workspace_membership(engine, WORKSPACE)
    lookup: CurrentWorkspaceContextLookup = DatabaseCurrentWorkspaceContexts(engine)

    assert lookup.resolve_current_workspace(USER) == CurrentWorkspaceContext(
        USER, WORKSPACE
    )


@pytest.mark.parametrize("user_status", ["inactive"])
def test_inactive_user_is_neutral_absence(engine: Engine, user_status: str) -> None:
    _add_user(engine, user_status)
    _add_workspace_membership(engine, WORKSPACE)
    assert DatabaseCurrentWorkspaceContexts(engine).resolve_current_workspace(USER) is None


@pytest.mark.parametrize(
    ("workspace_status", "membership_status"),
    [("inactive", "active"), ("active", "inactive")],
)
def test_inactive_workspace_or_membership_is_neutral_absence(
    engine: Engine, workspace_status: str, membership_status: str
) -> None:
    _add_user(engine)
    _add_workspace_membership(
        engine,
        WORKSPACE,
        workspace_status=workspace_status,
        membership_status=membership_status,
    )
    assert DatabaseCurrentWorkspaceContexts(engine).resolve_current_workspace(USER) is None


def test_multiple_active_memberships_do_not_select_a_workspace(engine: Engine) -> None:
    _add_user(engine)
    _add_workspace_membership(engine, WORKSPACE)
    _add_workspace_membership(engine, WorkspaceId("other-workspace-2656"))

    assert DatabaseCurrentWorkspaceContexts(engine).resolve_current_workspace(USER) is None


def test_committed_deactivation_affects_later_resolution(engine: Engine) -> None:
    _add_user(engine)
    _add_workspace_membership(engine, WORKSPACE)
    lookup = DatabaseCurrentWorkspaceContexts(engine)
    assert lookup.resolve_current_workspace(USER) is not None

    with engine.begin() as connection:
        connection.execute(
            text("UPDATE workspace_memberships SET status='inactive'")
        )
    assert lookup.resolve_current_workspace(USER) is None


def test_unmigrated_store_is_detail_free_unavailability(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    lookup = DatabaseCurrentWorkspaceContexts(engine)
    try:
        with pytest.raises(WorkspaceMembershipStoreUnavailable) as raised:
            lookup.resolve_current_workspace(USER)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(lookup) == "DatabaseCurrentWorkspaceContexts()"
    finally:
        engine.dispose()
