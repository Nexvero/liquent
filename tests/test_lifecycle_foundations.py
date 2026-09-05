from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.lifecycle import (
    UserLifecycleChangeId,
    UserLifecycleRevisionId,
    WorkspaceLifecycleChangeId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.ports import (
    UserLifecycleManagementAuthorityLookup,
    WorkspaceLifecycleManagementAuthorityLookup,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    LifecycleAuthorityStoreUnavailable,
)
from liquent_platform.persistence.lifecycle_authority import (
    DatabaseUserLifecycleManagementAuthority,
    DatabaseWorkspaceLifecycleManagementAuthority,
)
from liquent_platform.persistence.migrate import upgrade_to_head

ACTOR = UserId("actor-220")
IDENTIFIERS = (
    UserLifecycleRevisionId,
    UserLifecycleChangeId,
    WorkspaceLifecycleRevisionId,
    WorkspaceLifecycleChangeId,
)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'lifecycle.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


@pytest.mark.parametrize("kind", IDENTIFIERS)
def test_identifiers_are_immutable_slotted_and_repr_free(kind) -> None:
    identifier = kind("opaque-220")
    assert identifier.value == "opaque-220"
    assert "opaque-220" not in repr(identifier)
    assert not hasattr(identifier, "__dict__")
    with pytest.raises(FrozenInstanceError):
        identifier.value = "other"  # type: ignore[misc]


@pytest.mark.parametrize("kind", IDENTIFIERS)
@pytest.mark.parametrize("value", ["", None, 1, True, b"bytes"])
def test_identifiers_reject_invalid_values(kind, value) -> None:
    with pytest.raises(ValueError):
        kind(value)


def test_secure_material_draws_four_independent_ids(monkeypatch) -> None:
    values = iter(f"lifecycle-220-{index}" for index in range(4))
    monkeypatch.setattr("secrets.token_urlsafe", lambda _: next(values))
    material = SecureIdentityAuthorityMaterialGenerator()
    generated = (
        material.new_user_lifecycle_revision_id(),
        material.new_user_lifecycle_change_id(),
        material.new_workspace_lifecycle_revision_id(),
        material.new_workspace_lifecycle_change_id(),
    )
    assert tuple(item.value for item in generated) == tuple(
        f"lifecycle-220-{index}" for index in range(4)
    )


def _facts(
    engine: Engine,
    *,
    actor_status: str = "active",
    user_authority: str | None = "active",
    workspace_authority: str | None = "active",
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:actor,:status)"),
            {"actor": str(ACTOR).encode(), "status": actor_status},
        )
        for table, status in (
            ("user_lifecycle_management_authorities", user_authority),
            ("workspace_lifecycle_management_authorities", workspace_authority),
        ):
            if status is not None:
                connection.execute(
                    text(f"INSERT INTO {table} VALUES (:actor,:status)"),
                    {"actor": str(ACTOR).encode(), "status": status},
                )


def test_dedicated_active_authorities_permit_independently(engine: Engine) -> None:
    _facts(engine)
    principal = SessionPrincipal(ACTOR)
    users: UserLifecycleManagementAuthorityLookup = (
        DatabaseUserLifecycleManagementAuthority(engine)
    )
    workspaces: WorkspaceLifecycleManagementAuthorityLookup = (
        DatabaseWorkspaceLifecycleManagementAuthority(engine)
    )
    assert users.permits_user_lifecycle_management(principal) is True
    assert workspaces.permits_workspace_lifecycle_management(principal) is True


@pytest.mark.parametrize("domain", ["user", "workspace"])
def test_absence_inactivity_and_revocation_fail_closed(
    engine: Engine, domain: str
) -> None:
    _facts(
        engine,
        user_authority=None if domain == "user" else "active",
        workspace_authority=None if domain == "workspace" else "active",
    )
    principal = SessionPrincipal(ACTOR)
    lookup = (
        DatabaseUserLifecycleManagementAuthority(engine)
        if domain == "user"
        else DatabaseWorkspaceLifecycleManagementAuthority(engine)
    )
    permits = (
        lookup.permits_user_lifecycle_management
        if domain == "user"
        else lookup.permits_workspace_lifecycle_management
    )
    assert permits(principal) is False


def test_actor_inactivity_revokes_both_later_decisions(engine: Engine) -> None:
    _facts(engine)
    principal = SessionPrincipal(ACTOR)
    users = DatabaseUserLifecycleManagementAuthority(engine)
    workspaces = DatabaseWorkspaceLifecycleManagementAuthority(engine)
    assert users.permits_user_lifecycle_management(principal) is True
    assert workspaces.permits_workspace_lifecycle_management(principal) is True
    with engine.begin() as connection:
        connection.execute(text("UPDATE identity_users SET status='inactive'"))
    assert users.permits_user_lifecycle_management(principal) is False
    assert workspaces.permits_workspace_lifecycle_management(principal) is False


def test_committed_authority_revocation_affects_only_its_domain(
    engine: Engine,
) -> None:
    _facts(engine)
    principal = SessionPrincipal(ACTOR)
    users = DatabaseUserLifecycleManagementAuthority(engine)
    workspaces = DatabaseWorkspaceLifecycleManagementAuthority(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE user_lifecycle_management_authorities SET status='inactive'"
        ))
    assert users.permits_user_lifecycle_management(principal) is False
    assert workspaces.permits_workspace_lifecycle_management(principal) is True


def test_foundations_start_completely_empty(engine: Engine) -> None:
    tables = (
        "user_lifecycle_management_authorities",
        "workspace_lifecycle_management_authorities",
        "user_lifecycle_revisions",
        "user_lifecycle_revision_members",
        "user_lifecycle_current_revision",
        "user_lifecycle_changes",
        "workspace_lifecycle_revisions",
        "workspace_lifecycle_revision_members",
        "workspace_lifecycle_current_revision",
        "workspace_lifecycle_changes",
    )
    with engine.connect() as connection:
        assert all(
            connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0
            for table in tables
        )


def test_workspace_change_shape_enforces_terminal_contract(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO identity_users VALUES (X'75','active')"))
        connection.execute(text(
            "INSERT INTO identity_workspaces VALUES (X'77','active')"
        ))
        connection.execute(text(
            "INSERT INTO workspace_lifecycle_revisions VALUES (X'72')"
        ))
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO workspace_lifecycle_changes VALUES "
                "(X'63',X'75',X'77',NULL,'create',X'72',X'72')"
            ))
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO workspace_lifecycle_changes VALUES "
                "(X'64',X'75',X'77',X'75','reactivate',X'72',X'72')"
            ))


def test_unmigrated_lookup_is_detail_free(tmp_path: Path) -> None:
    database = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    lookup = DatabaseUserLifecycleManagementAuthority(database)
    try:
        with pytest.raises(LifecycleAuthorityStoreUnavailable) as raised:
            lookup.permits_user_lifecycle_management(SessionPrincipal(ACTOR))
        assert raised.value.args == ("lifecycle_authority_store_unavailable",)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(lookup) == "DatabaseUserLifecycleManagementAuthority()"
    finally:
        database.dispose()
