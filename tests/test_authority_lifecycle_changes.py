from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    AuthorizedWorkspaceMembershipAuthorityLifecycleChange,
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityLifecycleIntent,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    AuthorizedOidcTrustAuthorityLifecycleChange,
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityLifecycleIntent,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.ports import (
    AuthorizedOidcTrustAuthorityLifecycleStore,
    AuthorizedWorkspaceMembershipAuthorityLifecycleStore,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityLifecycleConflict,
    OidcTrustAuthorityLifecycleUnavailable,
    WorkspaceMembershipAuthorityLifecycleConflict,
    WorkspaceMembershipAuthorityLifecycleUnavailable,
)
from liquent_platform.persistence.membership_authority_anchor import (
    DatabaseWorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.persistence.membership_authority_lifecycle import (
    DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle,
)
from liquent_platform.persistence.membership_management_authority import (
    DatabaseWorkspaceMembershipManagementAuthority,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)
from liquent_platform.persistence.oidc_trust_authority_lifecycle import (
    DatabaseAuthorizedOidcTrustAuthorityLifecycle,
)
from liquent_platform.persistence.oidc_trust_authority import (
    DatabaseOidcTrustManagementAuthority,
)

ACTOR = UserId("lifecycle-actor")
TARGET = UserId("lifecycle-target")
WORKSPACE = WorkspaceId("lifecycle-workspace")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'lifecycle.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(engine: Engine) -> None:
    with engine.begin() as connection:
        for user in (ACTOR, TARGET):
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,'active')"),
                {"user": user.encode()},
            )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": WORKSPACE.encode()},
        )


def _global_anchor(engine: Engine) -> OidcTrustAuthoritySetRevisionId:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO oidc_trust_management_authorities VALUES"
                 " (:actor,'active')"),
            {"actor": ACTOR.encode()},
        )
    revision = OidcTrustAuthoritySetRevisionId("global-anchor-revision")
    outcome = DatabaseOidcTrustAuthoritySetAnchor(
        engine, generate_revision_id=lambda: revision
    ).anchor(
        OidcTrustAuthorityLifecycleChangeId("global-anchor-change"),
        SessionPrincipal(ACTOR),
    )
    assert outcome is not None
    return revision


def _workspace_anchor(engine: Engine) -> WorkspaceMembershipAuthoritySetRevisionId:
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:actor,:workspace,'active')"
        ), {"actor": ACTOR.encode(), "workspace": WORKSPACE.encode()})
    revision = WorkspaceMembershipAuthoritySetRevisionId(
        "workspace-anchor-revision"
    )
    outcome = DatabaseWorkspaceMembershipAuthoritySetAnchor(
        engine, generate_revision_id=lambda: revision
    ).anchor(
        WorkspaceMembershipAuthorityLifecycleChangeId("workspace-anchor-change"),
        SessionPrincipal(ACTOR),
        WORKSPACE,
    )
    assert outcome is not None
    return revision


def test_global_grant_deactivate_and_reactivate_form_complete_revisions(
    engine: Engine,
) -> None:
    _foundation(engine)
    expected = _global_anchor(engine)
    revisions = iter(
        OidcTrustAuthoritySetRevisionId(value)
        for value in ("global-grant", "global-deactivate", "global-reactivate")
    )
    port: AuthorizedOidcTrustAuthorityLifecycleStore = (
        DatabaseAuthorizedOidcTrustAuthorityLifecycle(
            engine, generate_revision_id=lambda: next(revisions)
        )
    )

    grant_id = OidcTrustAuthorityLifecycleChangeId("global-grant-change")
    grant = port.change_authority(
        grant_id, SessionPrincipal(ACTOR), TARGET,
        OidcTrustAuthorityLifecycleIntent.GRANT, expected,
    )
    assert grant == AuthorizedOidcTrustAuthorityLifecycleChange(
        grant_id, OidcTrustAuthoritySetRevisionId("global-grant"), TARGET,
        OidcTrustAuthorityLifecycleIntent.GRANT,
    )
    deactivate_id = OidcTrustAuthorityLifecycleChangeId("global-deactivate-change")
    deactivate = port.change_authority(
        deactivate_id, SessionPrincipal(ACTOR), ACTOR,
        OidcTrustAuthorityLifecycleIntent.DEACTIVATE,
        OidcTrustAuthoritySetRevisionId("global-grant"),
    )
    assert deactivate is not None
    reactivate_id = OidcTrustAuthorityLifecycleChangeId("global-reactivate-change")
    reactivate = port.change_authority(
        reactivate_id, SessionPrincipal(TARGET), ACTOR,
        OidcTrustAuthorityLifecycleIntent.REACTIVATE,
        OidcTrustAuthoritySetRevisionId("global-deactivate"),
    )
    assert reactivate is not None

    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT user_id,status FROM oidc_trust_management_authorities"
            " ORDER BY user_id"
        )).all() == [(ACTOR.encode(), "active"), (TARGET.encode(), "active")]
        assert connection.execute(text(
            "SELECT user_id,status FROM oidc_trust_authority_set_members"
            " WHERE revision_id=:revision ORDER BY user_id"
        ), {"revision": b"global-deactivate"}).all() == [
            (ACTOR.encode(), "inactive"), (TARGET.encode(), "active")
        ]


def test_workspace_grant_deactivate_and_reactivate_are_scope_bound(
    engine: Engine,
) -> None:
    _foundation(engine)
    expected = _workspace_anchor(engine)
    revisions = iter(
        WorkspaceMembershipAuthoritySetRevisionId(value)
        for value in ("workspace-grant", "workspace-deactivate", "workspace-reactivate")
    )
    port: AuthorizedWorkspaceMembershipAuthorityLifecycleStore = (
        DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
            engine, generate_revision_id=lambda: next(revisions)
        )
    )

    grant = port.change_authority(
        WorkspaceMembershipAuthorityLifecycleChangeId("workspace-grant-change"),
        SessionPrincipal(ACTOR), TARGET, WORKSPACE,
        WorkspaceMembershipAuthorityLifecycleIntent.GRANT, expected,
    )
    assert grant is not None
    deactivate = port.change_authority(
        WorkspaceMembershipAuthorityLifecycleChangeId(
            "workspace-deactivate-change"
        ),
        SessionPrincipal(ACTOR), ACTOR, WORKSPACE,
        WorkspaceMembershipAuthorityLifecycleIntent.DEACTIVATE,
        WorkspaceMembershipAuthoritySetRevisionId("workspace-grant"),
    )
    assert deactivate is not None
    reactivate = port.change_authority(
        WorkspaceMembershipAuthorityLifecycleChangeId(
            "workspace-reactivate-change"
        ),
        SessionPrincipal(TARGET), ACTOR, WORKSPACE,
        WorkspaceMembershipAuthorityLifecycleIntent.REACTIVATE,
        WorkspaceMembershipAuthoritySetRevisionId("workspace-deactivate"),
    )
    assert reactivate == AuthorizedWorkspaceMembershipAuthorityLifecycleChange(
        WorkspaceMembershipAuthorityLifecycleChangeId(
            "workspace-reactivate-change"
        ),
        WorkspaceMembershipAuthoritySetRevisionId("workspace-reactivate"),
        ACTOR,
        WORKSPACE,
        WorkspaceMembershipAuthorityLifecycleIntent.REACTIVATE,
    )


@pytest.mark.parametrize("domain", ["global", "workspace"])
def test_last_effective_manager_cannot_be_deactivated(
    engine: Engine, domain: str
) -> None:
    _foundation(engine)
    if domain == "global":
        expected = _global_anchor(engine)
        outcome = DatabaseAuthorizedOidcTrustAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId("unused"),
        ).change_authority(
            OidcTrustAuthorityLifecycleChangeId("last-global"),
            SessionPrincipal(ACTOR), ACTOR,
            OidcTrustAuthorityLifecycleIntent.DEACTIVATE, expected,
        )
    else:
        expected = _workspace_anchor(engine)
        outcome = DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: (
                WorkspaceMembershipAuthoritySetRevisionId("unused")
            ),
        ).change_authority(
            WorkspaceMembershipAuthorityLifecycleChangeId("last-workspace"),
            SessionPrincipal(ACTOR), ACTOR, WORKSPACE,
            WorkspaceMembershipAuthorityLifecycleIntent.DEACTIVATE, expected,
        )
    assert outcome is None


@pytest.mark.parametrize("domain", ["global", "workspace"])
def test_stale_revision_is_neutral_and_does_not_draw(
    engine: Engine, domain: str
) -> None:
    _foundation(engine)
    draws = 0

    def generate():
        nonlocal draws
        draws += 1
        raise AssertionError

    if domain == "global":
        _global_anchor(engine)
        outcome = DatabaseAuthorizedOidcTrustAuthorityLifecycle(
            engine, generate_revision_id=generate
        ).change_authority(
            OidcTrustAuthorityLifecycleChangeId("stale-global"),
            SessionPrincipal(ACTOR), TARGET,
            OidcTrustAuthorityLifecycleIntent.GRANT,
            OidcTrustAuthoritySetRevisionId("stale"),
        )
    else:
        _workspace_anchor(engine)
        outcome = DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
            engine, generate_revision_id=generate
        ).change_authority(
            WorkspaceMembershipAuthorityLifecycleChangeId("stale-workspace"),
            SessionPrincipal(ACTOR), TARGET, WORKSPACE,
            WorkspaceMembershipAuthorityLifecycleIntent.GRANT,
            WorkspaceMembershipAuthoritySetRevisionId("stale"),
        )
    assert outcome is None
    assert draws == 0


def test_exact_retry_returns_global_result_after_actor_revocation(
    engine: Engine,
) -> None:
    _foundation(engine)
    expected = _global_anchor(engine)
    change_id = OidcTrustAuthorityLifecycleChangeId("retry-global-lifecycle")
    store = DatabaseAuthorizedOidcTrustAuthorityLifecycle(
        engine,
        generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
            "retry-global-result"
        ),
    )
    result = store.change_authority(
        change_id, SessionPrincipal(ACTOR), TARGET,
        OidcTrustAuthorityLifecycleIntent.GRANT, expected,
    )
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE oidc_trust_management_authorities SET status='inactive'"
            " WHERE user_id=:actor"
        ), {"actor": ACTOR.encode()})

    assert store.change_authority(
        change_id, SessionPrincipal(ACTOR), TARGET,
        OidcTrustAuthorityLifecycleIntent.GRANT, expected,
    ) == result


def test_exact_retry_returns_workspace_result_after_actor_revocation(
    engine: Engine,
) -> None:
    _foundation(engine)
    expected = _workspace_anchor(engine)
    change_id = WorkspaceMembershipAuthorityLifecycleChangeId(
        "retry-workspace-lifecycle"
    )
    store = DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
        engine,
        generate_revision_id=lambda: WorkspaceMembershipAuthoritySetRevisionId(
            "retry-workspace-result"
        ),
    )
    result = store.change_authority(
        change_id, SessionPrincipal(ACTOR), TARGET, WORKSPACE,
        WorkspaceMembershipAuthorityLifecycleIntent.GRANT, expected,
    )
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE workspace_membership_management_authorities"
            " SET status='inactive' WHERE user_id=:actor"
            " AND workspace_id=:workspace"
        ), {"actor": ACTOR.encode(), "workspace": WORKSPACE.encode()})

    assert store.change_authority(
        change_id, SessionPrincipal(ACTOR), TARGET, WORKSPACE,
        WorkspaceMembershipAuthorityLifecycleIntent.GRANT, expected,
    ) == result


@pytest.mark.parametrize("domain", ["global", "workspace"])
def test_committed_deactivation_blocks_the_actors_next_authority_decision(
    engine: Engine, domain: str
) -> None:
    _foundation(engine)
    if domain == "global":
        expected = _global_anchor(engine)
        store = DatabaseAuthorizedOidcTrustAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                "revocation-grant"
            ),
        )
        grant = store.change_authority(
            OidcTrustAuthorityLifecycleChangeId("revocation-grant-change"),
            SessionPrincipal(ACTOR), TARGET,
            OidcTrustAuthorityLifecycleIntent.GRANT, expected,
        )
        assert grant is not None
        store = DatabaseAuthorizedOidcTrustAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                "revocation-deactivate"
            ),
        )
        assert store.change_authority(
            OidcTrustAuthorityLifecycleChangeId("revocation-deactivate-change"),
            SessionPrincipal(TARGET), ACTOR,
            OidcTrustAuthorityLifecycleIntent.DEACTIVATE, grant.revision_id,
        )
        assert DatabaseOidcTrustManagementAuthority(
            engine
        ).permits_oidc_trust_management(SessionPrincipal(ACTOR)) is False
    else:
        expected = _workspace_anchor(engine)
        store = DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: (
                WorkspaceMembershipAuthoritySetRevisionId("revocation-grant")
            ),
        )
        grant = store.change_authority(
            WorkspaceMembershipAuthorityLifecycleChangeId(
                "revocation-grant-change"
            ),
            SessionPrincipal(ACTOR), TARGET, WORKSPACE,
            WorkspaceMembershipAuthorityLifecycleIntent.GRANT, expected,
        )
        assert grant is not None
        store = DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: (
                WorkspaceMembershipAuthoritySetRevisionId(
                    "revocation-deactivate"
                )
            ),
        )
        assert store.change_authority(
            WorkspaceMembershipAuthorityLifecycleChangeId(
                "revocation-deactivate-change"
            ),
            SessionPrincipal(TARGET), ACTOR, WORKSPACE,
            WorkspaceMembershipAuthorityLifecycleIntent.DEACTIVATE,
            grant.revision_id,
        )
        assert DatabaseWorkspaceMembershipManagementAuthority(
            engine
        ).permits_workspace_membership_management(
            SessionPrincipal(ACTOR), WORKSPACE
        ) is False


@pytest.mark.parametrize("domain", ["global", "workspace"])
def test_change_id_reuse_with_different_intent_is_conflict(
    engine: Engine, domain: str
) -> None:
    _foundation(engine)
    if domain == "global":
        expected = _global_anchor(engine)
        change = OidcTrustAuthorityLifecycleChangeId("conflict-global-lifecycle")
        store = DatabaseAuthorizedOidcTrustAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                "conflict-global-result"
            ),
        )
        assert store.change_authority(
            change, SessionPrincipal(ACTOR), TARGET,
            OidcTrustAuthorityLifecycleIntent.GRANT, expected,
        )
        with pytest.raises(OidcTrustAuthorityLifecycleConflict):
            store.change_authority(
                change, SessionPrincipal(ACTOR), TARGET,
                OidcTrustAuthorityLifecycleIntent.REACTIVATE, expected,
            )
    else:
        expected = _workspace_anchor(engine)
        change = WorkspaceMembershipAuthorityLifecycleChangeId(
            "conflict-workspace-lifecycle"
        )
        store = DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
            engine,
            generate_revision_id=lambda: (
                WorkspaceMembershipAuthoritySetRevisionId(
                    "conflict-workspace-result"
                )
            ),
        )
        assert store.change_authority(
            change, SessionPrincipal(ACTOR), TARGET, WORKSPACE,
            WorkspaceMembershipAuthorityLifecycleIntent.GRANT, expected,
        )
        with pytest.raises(WorkspaceMembershipAuthorityLifecycleConflict):
            store.change_authority(
                change, SessionPrincipal(ACTOR), TARGET, WORKSPACE,
                WorkspaceMembershipAuthorityLifecycleIntent.REACTIVATE, expected,
            )


@pytest.mark.parametrize("domain", ["global", "workspace"])
def test_unmigrated_store_is_detail_free_unavailable(
    tmp_path: Path, domain: str
) -> None:
    database = build_engine(f"sqlite:///{tmp_path / domain}.db")
    try:
        if domain == "global":
            store = DatabaseAuthorizedOidcTrustAuthorityLifecycle(
                database,
                generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                    "unused"
                ),
            )
            with pytest.raises(OidcTrustAuthorityLifecycleUnavailable) as raised:
                store.change_authority(
                    OidcTrustAuthorityLifecycleChangeId("unavailable-global"),
                    SessionPrincipal(ACTOR), TARGET,
                    OidcTrustAuthorityLifecycleIntent.GRANT,
                    OidcTrustAuthoritySetRevisionId("expected"),
                )
        else:
            store = DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
                database,
                generate_revision_id=lambda: (
                    WorkspaceMembershipAuthoritySetRevisionId("unused")
                ),
            )
            with pytest.raises(
                WorkspaceMembershipAuthorityLifecycleUnavailable
            ) as raised:
                store.change_authority(
                    WorkspaceMembershipAuthorityLifecycleChangeId(
                        "unavailable-workspace"
                    ),
                    SessionPrincipal(ACTOR), TARGET, WORKSPACE,
                    WorkspaceMembershipAuthorityLifecycleIntent.GRANT,
                    WorkspaceMembershipAuthoritySetRevisionId("expected"),
                )
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
    finally:
        database.dispose()
