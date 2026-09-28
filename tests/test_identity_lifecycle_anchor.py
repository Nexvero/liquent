from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.lifecycle import (
    AnchoredIdentityLifecycleFoundation,
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.ports import InitialIdentityLifecycleFoundationAnchor
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    IdentityLifecycleFoundationAnchorUnavailable,
)
from liquent_platform.persistence.identity_lifecycle_anchor import (
    DatabaseInitialIdentityLifecycleFoundationAnchor,
)
from liquent_platform.persistence.migrate import upgrade_to_head

USER = UserId("anchor-user-221")
WORKSPACE = WorkspaceId("anchor-workspace-221")
USER_REVISION = UserLifecycleRevisionId("anchor-user-revision-221")
WORKSPACE_REVISION = WorkspaceLifecycleRevisionId("anchor-workspace-revision-221")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'anchor.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _canonical(engine: Engine, *, active: bool = True) -> None:
    status = "active" if active else "inactive"
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:user,:status)"),
            {"user": USER.encode(), "status": status},
        )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,:status)"),
            {"workspace": WORKSPACE.encode(), "status": status},
        )
        connection.execute(text(
            "INSERT INTO workspace_onboarding_management"
            " VALUES (:user,:workspace,:status)"
        ), {"user": USER.encode(), "workspace": WORKSPACE.encode(), "status": status})


def _store(engine: Engine) -> DatabaseInitialIdentityLifecycleFoundationAnchor:
    return DatabaseInitialIdentityLifecycleFoundationAnchor(
        engine,
        generate_user_revision_id=lambda: USER_REVISION,
        generate_workspace_revision_id=lambda: WORKSPACE_REVISION,
    )


def test_exact_canonical_inventory_is_anchored_atomically(engine: Engine) -> None:
    _canonical(engine)
    port: InitialIdentityLifecycleFoundationAnchor = _store(engine)
    assert port.anchor() == AnchoredIdentityLifecycleFoundation(
        USER, WORKSPACE, USER_REVISION, WORKSPACE_REVISION
    )
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM user_lifecycle_management_authorities),"
            " (SELECT count(*) FROM workspace_lifecycle_management_authorities),"
            " (SELECT count(*) FROM user_lifecycle_current_revision),"
            " (SELECT count(*) FROM workspace_lifecycle_current_revision)"
        )).one() == (1, 1, 1, 1)


@pytest.mark.parametrize("variant", ["empty", "inactive", "additional"])
def test_noncanonical_inventory_is_neutral(engine: Engine, variant: str) -> None:
    if variant != "empty":
        _canonical(engine, active=variant != "inactive")
    if variant == "additional":
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO identity_users VALUES (X'78','active')"
            ))
    assert _store(engine).anchor() is None


def test_success_closes_anchor_permanently(engine: Engine) -> None:
    _canonical(engine)
    assert _store(engine).anchor() is not None
    assert _store(engine).anchor() is None


def test_invalid_generated_revision_rolls_back(engine: Engine) -> None:
    _canonical(engine)
    store = DatabaseInitialIdentityLifecycleFoundationAnchor(
        engine,
        generate_user_revision_id=lambda: USER_REVISION,
        generate_workspace_revision_id=lambda: "invalid",  # type: ignore[arg-type]
    )
    with pytest.raises(IdentityLifecycleFoundationAnchorUnavailable):
        store.anchor()
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM user_lifecycle_management_authorities"
        )) == 0


def test_unmigrated_store_is_detail_free(tmp_path: Path) -> None:
    database = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = _store(database)
    try:
        with pytest.raises(IdentityLifecycleFoundationAnchorUnavailable) as raised:
            store.anchor()
        assert raised.value.args == (
            "identity_lifecycle_foundation_anchor_unavailable",
        )
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseInitialIdentityLifecycleFoundationAnchor()"
    finally:
        database.dispose()
