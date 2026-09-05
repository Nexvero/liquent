from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipChangeId,
    WorkspaceMembershipRevisionId,
)
from liquent_platform.identity.ports import (
    WorkspaceMembershipManagementAuthorityLookup,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipManagementAuthorityUnavailable,
)
from liquent_platform.persistence.membership_management_authority import (
    DatabaseWorkspaceMembershipManagementAuthority,
)
from liquent_platform.persistence.migrate import upgrade_to_head

ACTOR = UserId("membership-manager")
WORKSPACE = WorkspaceId("managed-workspace")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'management.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(
    engine: Engine, *, actor: str = "active", workspace: str = "active",
    authority: str | None = "active",
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:actor,:status)"),
            {"actor": ACTOR.encode(), "status": actor},
        )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,:status)"),
            {"workspace": WORKSPACE.encode(), "status": workspace},
        )
        if authority is not None:
            connection.execute(text(
                "INSERT INTO workspace_membership_management_authorities"
                " (user_id,workspace_id,status) VALUES (:actor,:workspace,:status)"
            ), {
                "actor": ACTOR.encode(), "workspace": WORKSPACE.encode(),
                "status": authority,
            })


@pytest.mark.parametrize(
    "kind", [WorkspaceMembershipRevisionId, WorkspaceMembershipChangeId]
)
def test_internal_identifiers_are_immutable_slotted_and_repr_free(kind) -> None:
    identifier = kind("opaque-207")

    assert [item.name for item in fields(kind)] == ["value"]
    assert "opaque-207" not in repr(identifier)
    assert not hasattr(identifier, "__dict__")
    with pytest.raises(FrozenInstanceError):
        identifier.value = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    "kind", [WorkspaceMembershipRevisionId, WorkspaceMembershipChangeId]
)
@pytest.mark.parametrize("value", ["", None, 1, b"bytes"])
def test_internal_identifiers_reject_empty_and_non_string_values(kind, value) -> None:
    with pytest.raises(ValueError):
        kind(value)


def test_secure_material_draws_independent_membership_identifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(["revision-207", "change-207"])
    monkeypatch.setattr("secrets.token_urlsafe", lambda _: next(values))
    material = SecureIdentityAuthorityMaterialGenerator()

    assert material.new_workspace_membership_revision_id() == (
        WorkspaceMembershipRevisionId("revision-207")
    )
    assert material.new_workspace_membership_change_id() == (
        WorkspaceMembershipChangeId("change-207")
    )


def test_active_actor_workspace_and_dedicated_authority_are_required(
    engine: Engine,
) -> None:
    _foundation(engine)
    lookup: WorkspaceMembershipManagementAuthorityLookup = (
        DatabaseWorkspaceMembershipManagementAuthority(engine)
    )

    assert lookup.permits_workspace_membership_management(
        SessionPrincipal(ACTOR), WORKSPACE
    ) is True
    assert lookup.permits_workspace_membership_management(
        SessionPrincipal(ACTOR), WorkspaceId("other")
    ) is False


@pytest.mark.parametrize(
    ("actor", "workspace", "authority"),
    [
        ("inactive", "active", "active"),
        ("active", "inactive", "active"),
        ("active", "active", "inactive"),
        ("active", "active", None),
    ],
)
def test_absence_and_inactivity_fail_closed(
    engine: Engine, actor: str, workspace: str, authority: str | None
) -> None:
    _foundation(
        engine, actor=actor, workspace=workspace, authority=authority
    )
    lookup = DatabaseWorkspaceMembershipManagementAuthority(engine)

    assert lookup.permits_workspace_membership_management(
        SessionPrincipal(ACTOR), WORKSPACE
    ) is False


def test_onboarding_authority_and_research_permissions_do_not_substitute(
    engine: Engine,
) -> None:
    _foundation(engine, authority=None)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO workspace_onboarding_management VALUES"
            " (:actor,:workspace,'active')"
        ), {"actor": ACTOR.encode(), "workspace": WORKSPACE.encode()})
        connection.execute(text(
            "INSERT INTO workspace_memberships"
            " (user_id,workspace_id,status) VALUES (:actor,:workspace,'active')"
        ), {"actor": ACTOR.encode(), "workspace": WORKSPACE.encode()})
        connection.execute(text(
            "INSERT INTO workspace_membership_permissions VALUES"
            " (:actor,:workspace,'research:write')"
        ), {"actor": ACTOR.encode(), "workspace": WORKSPACE.encode()})

    assert DatabaseWorkspaceMembershipManagementAuthority(
        engine
    ).permits_workspace_membership_management(
        SessionPrincipal(ACTOR), WORKSPACE
    ) is False


def test_committed_revocation_affects_the_next_lookup(engine: Engine) -> None:
    _foundation(engine)
    lookup = DatabaseWorkspaceMembershipManagementAuthority(engine)
    assert lookup.permits_workspace_membership_management(
        SessionPrincipal(ACTOR), WORKSPACE
    ) is True
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE workspace_membership_management_authorities"
            " SET status='inactive'"
        ))
    assert lookup.permits_workspace_membership_management(
        SessionPrincipal(ACTOR), WORKSPACE
    ) is False


def test_new_foundation_is_empty_and_existing_membership_is_not_adopted(
    engine: Engine,
) -> None:
    with engine.connect() as connection:
        for table in (
            "workspace_membership_management_authorities",
            "workspace_membership_revisions",
            "workspace_membership_revision_permissions",
            "authorized_workspace_membership_changes",
        ):
            assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0
    _foundation(engine, authority=None)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO workspace_memberships"
            " (user_id,workspace_id,status) VALUES (:actor,:workspace,'active')"
        ), {"actor": ACTOR.encode(), "workspace": WORKSPACE.encode()})
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT revision_id FROM workspace_memberships"
        )) is None
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_revisions"
        )) == 0


def test_unmigrated_store_is_detail_free_technical_unavailability(
    tmp_path: Path,
) -> None:
    database = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    lookup = DatabaseWorkspaceMembershipManagementAuthority(database)
    try:
        with pytest.raises(
            WorkspaceMembershipManagementAuthorityUnavailable
        ) as raised:
            lookup.permits_workspace_membership_management(
                SessionPrincipal(ACTOR), WORKSPACE
            )
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(lookup) == (
            "DatabaseWorkspaceMembershipManagementAuthority()"
        )
    finally:
        database.dispose()
