from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    AnchoredWorkspaceMembershipAuthoritySet,
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    AnchoredOidcTrustAuthoritySet,
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.ports import (
    OidcTrustAuthoritySetAnchor,
    WorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityAnchorConflict,
    OidcTrustAuthorityAnchorUnavailable,
    WorkspaceMembershipAuthorityAnchorConflict,
    WorkspaceMembershipAuthorityAnchorUnavailable,
)
from liquent_platform.persistence.membership_authority_anchor import (
    DatabaseWorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)

ACTOR = UserId("anchor-actor")
OTHER = UserId("anchor-other")
WORKSPACE = WorkspaceId("anchor-workspace")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'anchors.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(engine: Engine) -> None:
    with engine.begin() as connection:
        for user in (ACTOR, OTHER):
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,'active')"),
                {"user": user.encode()},
            )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": WORKSPACE.encode()},
        )


def _oidc_store(
    engine: Engine, revision: str = "oidc-anchor-revision"
) -> DatabaseOidcTrustAuthoritySetAnchor:
    return DatabaseOidcTrustAuthoritySetAnchor(
        engine,
        generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(revision),
    )


def _membership_store(
    engine: Engine, revision: str = "membership-anchor-revision"
) -> DatabaseWorkspaceMembershipAuthoritySetAnchor:
    return DatabaseWorkspaceMembershipAuthoritySetAnchor(
        engine,
        generate_revision_id=lambda: WorkspaceMembershipAuthoritySetRevisionId(
            revision
        ),
    )


def test_global_anchor_persists_complete_existing_set_without_status_change(
    engine: Engine,
) -> None:
    _foundation(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities VALUES"
            " (:actor,'active'),(:other,'inactive')"
        ), {"actor": ACTOR.encode(), "other": OTHER.encode()})
    change = OidcTrustAuthorityLifecycleChangeId("oidc-anchor-change")
    port: OidcTrustAuthoritySetAnchor = _oidc_store(engine)

    assert port.anchor(change, SessionPrincipal(ACTOR)) == (
        AnchoredOidcTrustAuthoritySet(
            change, OidcTrustAuthoritySetRevisionId("oidc-anchor-revision")
        )
    )
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT user_id,status FROM oidc_trust_authority_set_members"
            " ORDER BY user_id"
        )).all() == [
            (ACTOR.encode(), "active"),
            (OTHER.encode(), "inactive"),
        ]
        assert connection.execute(text(
            "SELECT user_id,status FROM oidc_trust_management_authorities"
            " ORDER BY user_id"
        )).all() == [
            (ACTOR.encode(), "active"),
            (OTHER.encode(), "inactive"),
        ]
        assert connection.execute(text(
            "SELECT actor_user_id,target_user_id,intent,expected_revision_id"
            " FROM oidc_trust_authority_lifecycle_changes"
        )).one() == (ACTOR.encode(), ACTOR.encode(), "anchor", None)


def test_workspace_anchor_is_scoped_and_leaves_other_workspace_unanchored(
    engine: Engine,
) -> None:
    _foundation(engine)
    other_workspace = WorkspaceId("other-anchor-workspace")
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": other_workspace.encode()},
        )
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:actor,:workspace,'active'),(:other,:workspace,'inactive'),"
            " (:other,:other_workspace,'active')"
        ), {
            "actor": ACTOR.encode(), "other": OTHER.encode(),
            "workspace": WORKSPACE.encode(),
            "other_workspace": other_workspace.encode(),
        })
    change = WorkspaceMembershipAuthorityLifecycleChangeId("member-anchor-change")
    port: WorkspaceMembershipAuthoritySetAnchor = _membership_store(engine)

    assert port.anchor(change, SessionPrincipal(ACTOR), WORKSPACE) == (
        AnchoredWorkspaceMembershipAuthoritySet(
            change,
            WorkspaceMembershipAuthoritySetRevisionId(
                "membership-anchor-revision"
            ),
            WORKSPACE,
        )
    )
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT user_id,status FROM workspace_membership_authority_set_members"
            " ORDER BY user_id"
        )).all() == [
            (ACTOR.encode(), "active"),
            (OTHER.encode(), "inactive"),
        ]
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_authority_current_sets"
            " WHERE workspace_id=:workspace"
        ), {"workspace": other_workspace.encode()}) == 0


@pytest.mark.parametrize("domain", ["oidc", "membership"])
def test_absent_or_inactive_actor_authority_is_neutral_and_draws_nothing(
    engine: Engine, domain: str
) -> None:
    _foundation(engine)
    draws = 0

    def generate():
        nonlocal draws
        draws += 1
        raise AssertionError

    if domain == "oidc":
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO oidc_trust_management_authorities VALUES"
                " (:actor,'inactive')"
            ), {"actor": ACTOR.encode()})
        outcome = DatabaseOidcTrustAuthoritySetAnchor(
            engine, generate_revision_id=generate
        ).anchor(
            OidcTrustAuthorityLifecycleChangeId("neutral-oidc"),
            SessionPrincipal(ACTOR),
        )
    else:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO workspace_membership_management_authorities VALUES"
                " (:actor,:workspace,'inactive')"
            ), {"actor": ACTOR.encode(), "workspace": WORKSPACE.encode()})
        outcome = DatabaseWorkspaceMembershipAuthoritySetAnchor(
            engine, generate_revision_id=generate
        ).anchor(
            WorkspaceMembershipAuthorityLifecycleChangeId("neutral-membership"),
            SessionPrincipal(ACTOR),
            WORKSPACE,
        )
    assert outcome is None
    assert draws == 0


def test_exact_global_retry_survives_later_authority_revocation(
    engine: Engine,
) -> None:
    _foundation(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities VALUES"
            " (:actor,'active')"
        ), {"actor": ACTOR.encode()})
    change = OidcTrustAuthorityLifecycleChangeId("retry-oidc-anchor")
    expected = _oidc_store(engine).anchor(change, SessionPrincipal(ACTOR))
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE oidc_trust_management_authorities SET status='inactive'"
        ))

    assert _oidc_store(engine, "must-not-be-used").anchor(
        change, SessionPrincipal(ACTOR)
    ) == expected


def test_exact_workspace_retry_survives_later_authority_revocation(
    engine: Engine,
) -> None:
    _foundation(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:actor,:workspace,'active')"
        ), {"actor": ACTOR.encode(), "workspace": WORKSPACE.encode()})
    change = WorkspaceMembershipAuthorityLifecycleChangeId("retry-member-anchor")
    expected = _membership_store(engine).anchor(
        change, SessionPrincipal(ACTOR), WORKSPACE
    )
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE workspace_membership_management_authorities"
            " SET status='inactive'"
        ))

    assert _membership_store(engine, "must-not-be-used").anchor(
        change, SessionPrincipal(ACTOR), WORKSPACE
    ) == expected


def test_reusing_global_change_id_with_another_actor_is_conflict(
    engine: Engine,
) -> None:
    _foundation(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities VALUES"
            " (:actor,'active'),(:other,'active')"
        ), {"actor": ACTOR.encode(), "other": OTHER.encode()})
    change = OidcTrustAuthorityLifecycleChangeId("conflict-oidc-anchor")
    assert _oidc_store(engine).anchor(change, SessionPrincipal(ACTOR))

    with pytest.raises(OidcTrustAuthorityAnchorConflict) as raised:
        _oidc_store(engine).anchor(change, SessionPrincipal(OTHER))
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_reusing_workspace_change_id_in_another_scope_is_conflict(
    engine: Engine,
) -> None:
    _foundation(engine)
    other_workspace = WorkspaceId("conflicting-workspace")
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": other_workspace.encode()},
        )
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:actor,:workspace,'active'),(:actor,:other_workspace,'active')"
        ), {
            "actor": ACTOR.encode(), "workspace": WORKSPACE.encode(),
            "other_workspace": other_workspace.encode(),
        })
    change = WorkspaceMembershipAuthorityLifecycleChangeId("conflict-member-anchor")
    assert _membership_store(engine).anchor(
        change, SessionPrincipal(ACTOR), WORKSPACE
    )

    with pytest.raises(WorkspaceMembershipAuthorityAnchorConflict):
        _membership_store(engine).anchor(
            change, SessionPrincipal(ACTOR), other_workspace
        )


@pytest.mark.parametrize("domain", ["oidc", "membership"])
def test_unmigrated_store_is_detail_free_technical_unavailability(
    tmp_path: Path, domain: str
) -> None:
    database = build_engine(f"sqlite:///{tmp_path / domain}.db")
    try:
        if domain == "oidc":
            store = _oidc_store(database)
            failure = OidcTrustAuthorityAnchorUnavailable
            call = lambda: store.anchor(  # noqa: E731
                OidcTrustAuthorityLifecycleChangeId("unavailable-oidc"),
                SessionPrincipal(ACTOR),
            )
        else:
            store = _membership_store(database)
            failure = WorkspaceMembershipAuthorityAnchorUnavailable
            call = lambda: store.anchor(  # noqa: E731
                WorkspaceMembershipAuthorityLifecycleChangeId(
                    "unavailable-membership"
                ),
                SessionPrincipal(ACTOR),
                WORKSPACE,
            )
        with pytest.raises(failure) as raised:
            call()
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert "anchor" not in str(raised.value).replace("_anchor_", "")
    finally:
        database.dispose()
