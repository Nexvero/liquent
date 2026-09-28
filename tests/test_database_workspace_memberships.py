from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.application.authorize_research import authorize_research
from liquent_platform.identity.access import (
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.ports import WorkspaceMembershipLookup
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipStoreUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.workspace_memberships import (
    DatabaseWorkspaceMemberships,
)

USER = UserId("user-195")
WORKSPACE = WorkspaceId("workspace-195")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'memberships.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(engine: Engine, *, user: str = "active", workspace: str = "active") -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users (user_id,status) VALUES (:id,:status)"),
            {"id": str(USER).encode(), "status": user},
        )
        connection.execute(
            text(
                "INSERT INTO identity_workspaces (workspace_id,status)"
                " VALUES (:id,:status)"
            ),
            {"id": str(WORKSPACE).encode(), "status": workspace},
        )


def _membership(
    engine: Engine,
    *,
    status: str = "active",
    permissions: tuple[str, ...] = (),
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO workspace_memberships (user_id,workspace_id,status)"
                " VALUES (:user,:workspace,:status)"
            ),
            {
                "user": str(USER).encode(),
                "workspace": str(WORKSPACE).encode(),
                "status": status,
            },
        )
        for permission in permissions:
            connection.execute(
                text(
                    "INSERT INTO workspace_membership_permissions"
                    " (user_id,workspace_id,permission)"
                    " VALUES (:user,:workspace,:permission)"
                ),
                {
                    "user": str(USER).encode(),
                    "workspace": str(WORKSPACE).encode(),
                    "permission": permission,
                },
            )


def test_lookup_satisfies_port_and_returns_exact_snapshot(engine: Engine) -> None:
    _foundation(engine)
    _membership(engine, permissions=("research:write", "research:read"))
    lookup: WorkspaceMembershipLookup = DatabaseWorkspaceMemberships(engine)

    assert lookup.get_membership(USER, WORKSPACE) == WorkspaceMembership(
        USER,
        WORKSPACE,
        MembershipStatus.ACTIVE,
        frozenset({Permission.RESEARCH_READ, Permission.RESEARCH_WRITE}),
    )


def test_active_membership_without_permissions_is_visible_but_denied(
    engine: Engine,
) -> None:
    _foundation(engine)
    _membership(engine)
    lookup = DatabaseWorkspaceMemberships(engine)
    membership = lookup.get_membership(USER, WORKSPACE)
    assert membership is not None and membership.permissions == frozenset()
    assert authorize_research(
        lookup,
        SessionPrincipal(USER),
        WORKSPACE,
        Permission.RESEARCH_READ,
    ) is False


def test_write_permission_keeps_existing_read_implication(engine: Engine) -> None:
    _foundation(engine)
    _membership(engine, permissions=("research:write",))
    lookup = DatabaseWorkspaceMemberships(engine)
    principal = SessionPrincipal(USER)
    assert authorize_research(
        lookup, principal, WORKSPACE, Permission.RESEARCH_WRITE
    ) is True
    assert authorize_research(
        lookup, principal, WORKSPACE, Permission.RESEARCH_READ
    ) is True


@pytest.mark.parametrize(
    ("user_status", "workspace_status", "membership_status", "expected"),
    [
        ("inactive", "active", "active", None),
        ("active", "inactive", "active", None),
        (
            "active",
            "active",
            "inactive",
            WorkspaceMembership(
                USER,
                WORKSPACE,
                MembershipStatus.INACTIVE,
                frozenset({Permission.RESEARCH_WRITE}),
            ),
        ),
    ],
)
def test_inactive_facts_fail_closed(
    engine: Engine,
    user_status: str,
    workspace_status: str,
    membership_status: str,
    expected: WorkspaceMembership | None,
) -> None:
    _foundation(engine, user=user_status, workspace=workspace_status)
    _membership(engine, status=membership_status, permissions=("research:write",))
    assert DatabaseWorkspaceMemberships(engine).get_membership(USER, WORKSPACE) == expected


def test_unknown_pair_is_neutral_none(engine: Engine) -> None:
    lookup = DatabaseWorkspaceMemberships(engine)
    assert lookup.get_membership(USER, WORKSPACE) is None
    assert lookup.get_membership(UserId("other"), WORKSPACE) is None


def test_later_permission_revocation_affects_later_decision(engine: Engine) -> None:
    _foundation(engine)
    _membership(engine, permissions=("research:write",))
    lookup = DatabaseWorkspaceMemberships(engine)
    principal = SessionPrincipal(USER)
    assert authorize_research(
        lookup, principal, WORKSPACE, Permission.RESEARCH_WRITE
    ) is True
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM workspace_membership_permissions")
        )
    assert authorize_research(
        lookup, principal, WORKSPACE, Permission.RESEARCH_WRITE
    ) is False


def test_unmigrated_store_is_detail_free_technical_unavailability(
    tmp_path: Path,
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    lookup = DatabaseWorkspaceMemberships(engine)
    try:
        with pytest.raises(WorkspaceMembershipStoreUnavailable) as raised:
            lookup.get_membership(USER, WORKSPACE)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(lookup) == "DatabaseWorkspaceMemberships()"
    finally:
        engine.dispose()
