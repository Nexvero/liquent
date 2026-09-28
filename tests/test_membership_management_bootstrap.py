from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    BootstrappedWorkspaceMembershipManagementAuthority,
)
from liquent_platform.identity.ports import (
    InitialWorkspaceMembershipManagementAuthorityBootstrap,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipManagementBootstrapUnavailable,
)
from liquent_platform.persistence.membership_management_bootstrap import (
    DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap,
)
from liquent_platform.persistence.migrate import upgrade_to_head

USER = UserId("manager-208")
OTHER_USER = UserId("other-manager-208")
WORKSPACE = WorkspaceId("workspace-208")
OTHER_WORKSPACE = WorkspaceId("other-workspace-208")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(
    engine: Engine,
    *,
    user: UserId = USER,
    workspace: WorkspaceId = WORKSPACE,
    user_status: str = "active",
    workspace_status: str = "active",
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:user,:status)"),
            {"user": user.encode(), "status": user_status},
        )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,:status)"),
            {"workspace": workspace.encode(), "status": workspace_status},
        )


def _bootstrap(
    engine: Engine, user: UserId = USER, workspace: WorkspaceId = WORKSPACE
):
    port: InitialWorkspaceMembershipManagementAuthorityBootstrap = (
        DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap(engine)
    )
    return port.bootstrap(user, workspace)


def test_first_active_user_is_granted_authority_for_active_workspace(
    engine: Engine,
) -> None:
    _foundation(engine)

    assert _bootstrap(engine) == (
        BootstrappedWorkspaceMembershipManagementAuthority(USER, WORKSPACE)
    )
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT user_id,workspace_id,status"
            " FROM workspace_membership_management_authorities"
        )).one() == (USER.encode(), WORKSPACE.encode(), "active")


@pytest.mark.parametrize(
    ("known_user", "known_workspace", "user_status", "workspace_status"),
    [
        (False, True, "active", "active"),
        (True, False, "active", "active"),
        (True, True, "inactive", "active"),
        (True, True, "active", "inactive"),
    ],
)
def test_unknown_or_inactive_foundation_is_neutral(
    engine: Engine,
    known_user: bool,
    known_workspace: bool,
    user_status: str,
    workspace_status: str,
) -> None:
    if known_user:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,:status)"),
                {"user": USER.encode(), "status": user_status},
            )
    if known_workspace:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO identity_workspaces VALUES (:workspace,:status)"),
                {"workspace": WORKSPACE.encode(), "status": workspace_status},
            )

    assert _bootstrap(engine) is None
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_management_authorities"
        )) == 0


def test_any_authority_history_closes_that_workspace_permanently(
    engine: Engine,
) -> None:
    _foundation(engine)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:user,'active')"),
            {"user": OTHER_USER.encode()},
        )
    assert _bootstrap(engine) is not None
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE workspace_membership_management_authorities"
            " SET status='inactive'"
        ))

    assert _bootstrap(engine, OTHER_USER) is None
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_management_authorities"
        )) == 1


def test_a_different_empty_workspace_has_its_own_bootstrap_scope(
    engine: Engine,
) -> None:
    _foundation(engine)
    _foundation(engine, user=OTHER_USER, workspace=OTHER_WORKSPACE)

    assert _bootstrap(engine) is not None
    assert _bootstrap(engine, OTHER_USER, OTHER_WORKSPACE) is not None
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_management_authorities"
        )) == 2


def test_bootstrap_creates_no_membership_permission_revision_or_change(
    engine: Engine,
) -> None:
    _foundation(engine)
    assert _bootstrap(engine) is not None
    with engine.connect() as connection:
        for table in (
            "workspace_memberships",
            "workspace_membership_permissions",
            "workspace_membership_revisions",
            "workspace_membership_revision_permissions",
            "authorized_workspace_membership_changes",
        ):
            assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0


def test_invalid_identifier_is_detail_free_technical_unavailability(
    engine: Engine,
) -> None:
    store = DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap(engine)
    with pytest.raises(
        WorkspaceMembershipManagementBootstrapUnavailable
    ) as raised:
        store.bootstrap(UserId(""), WORKSPACE)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_unmigrated_store_is_detail_free_technical_unavailability(
    tmp_path: Path,
) -> None:
    database = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap(database)
    try:
        with pytest.raises(
            WorkspaceMembershipManagementBootstrapUnavailable
        ) as raised:
            store.bootstrap(USER, WORKSPACE)
        assert raised.value.args == (
            "workspace_membership_management_bootstrap_unavailable",
        )
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == (
            "DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap()"
        )
    finally:
        database.dispose()
