from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import BootstrappedIdentityAuthority, UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.lifecycle import (
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.identity_errors import (
    IdentityAuthorityBootstrapUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head

USER = UserId("bootstrap-user")
WORKSPACE = WorkspaceId("bootstrap-workspace")
USER_REVISION = UserLifecycleRevisionId("bootstrap-user-revision")
WORKSPACE_REVISION = WorkspaceLifecycleRevisionId("bootstrap-workspace-revision")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


class Source:
    def __init__(self, value: object) -> None:
        self.value = value
        self.calls = 0

    def __call__(self) -> object:
        self.calls += 1
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


def _store(
    engine: Engine,
    user: Callable[[], UserId] | None = None,
    workspace: Callable[[], WorkspaceId] | None = None,
) -> DatabaseInitialIdentityAuthorityBootstrap:
    return DatabaseInitialIdentityAuthorityBootstrap(
        engine,
        generate_user_id=user or Source(USER),  # type: ignore[arg-type]
        generate_workspace_id=workspace or Source(WORKSPACE),  # type: ignore[arg-type]
        generate_user_revision_id=Source(USER_REVISION),  # type: ignore[arg-type]
        generate_workspace_revision_id=Source(  # type: ignore[arg-type]
            WORKSPACE_REVISION
        ),
    )


def _counts(engine: Engine) -> tuple[int, int, int]:
    with engine.connect() as connection:
        return (
            connection.scalar(text("SELECT count(*) FROM identity_users")),
            connection.scalar(text("SELECT count(*) FROM identity_workspaces")),
            connection.scalar(
                text("SELECT count(*) FROM workspace_onboarding_management")
            ),
        )


def test_empty_foundation_is_bootstrapped_atomically(engine: Engine) -> None:
    assert _store(engine).bootstrap() == BootstrappedIdentityAuthority(USER, WORKSPACE)
    assert _counts(engine) == (1, 1, 1)

    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT users.status, workspaces.status, authority.status"
                " FROM identity_users AS users"
                " JOIN workspace_onboarding_management AS authority"
                " ON authority.user_id=users.user_id"
                " JOIN identity_workspaces AS workspaces"
                " ON workspaces.workspace_id=authority.workspace_id"
            )
        ).one() == ("active", "active", "active")
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM user_lifecycle_management_authorities),"
            " (SELECT count(*) FROM workspace_lifecycle_management_authorities),"
            " (SELECT count(*) FROM user_lifecycle_current_revision),"
            " (SELECT count(*) FROM workspace_lifecycle_current_revision)"
        )).one() == (1, 1, 1, 1)
        assert connection.execute(text(
            "SELECT user_member.status,workspace_member.status"
            " FROM user_lifecycle_revision_members AS user_member"
            " CROSS JOIN workspace_lifecycle_revision_members AS workspace_member"
        )).one() == ("active", "active")


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO identity_users (user_id, status) VALUES (x'75', 'inactive')",
        "INSERT INTO identity_workspaces (workspace_id, status)"
        " VALUES (x'77', 'inactive')",
    ],
    ids=["user-inventory", "workspace-inventory"],
)
def test_any_existing_inventory_closes_without_generating(
    engine: Engine, statement: str
) -> None:
    with engine.begin() as connection:
        connection.execute(text(statement))
    user = Source(USER)
    workspace = Source(WORKSPACE)

    assert _store(engine, user, workspace).bootstrap() is None  # type: ignore[arg-type]
    assert user.calls == workspace.calls == 0


def test_existing_authority_inventory_closes_without_generating(engine: Engine) -> None:
    assert _store(engine).bootstrap() is not None
    user = Source(UserId("other-user"))
    workspace = Source(WorkspaceId("other-workspace"))

    assert _store(engine, user, workspace).bootstrap() is None  # type: ignore[arg-type]
    assert user.calls == workspace.calls == 0
    assert _counts(engine) == (1, 1, 1)


@pytest.mark.parametrize("failure", [RuntimeError("generator"), ""])
def test_generation_failure_rolls_back_without_partial_inventory(
    engine: Engine, failure: object
) -> None:
    workspace = Source(failure)

    with pytest.raises(IdentityAuthorityBootstrapUnavailable) as raised:
        _store(engine, Source(USER), workspace).bootstrap()  # type: ignore[arg-type]

    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert _counts(engine) == (0, 0, 0)


def test_technical_failure_is_detail_free(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = _store(engine)
    try:
        with pytest.raises(IdentityAuthorityBootstrapUnavailable) as raised:
            store.bootstrap()
        assert raised.value.args == ("identity_authority_bootstrap_unavailable",)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseInitialIdentityAuthorityBootstrap()"
    finally:
        engine.dispose()
