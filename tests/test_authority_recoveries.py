from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    RecoveredWorkspaceMembershipAuthoritySet,
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityRecoveryId,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityRecoveryId,
    OidcTrustAuthoritySetRevisionId,
    RecoveredOidcTrustAuthoritySet,
)
from liquent_platform.identity.ports import (
    OfflineOidcTrustAuthorityRecoveryStore,
    OfflineWorkspaceMembershipAuthorityRecoveryStore,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityRecoveryConflict,
    OidcTrustAuthorityRecoveryUnavailable,
    WorkspaceMembershipAuthorityRecoveryConflict,
    WorkspaceMembershipAuthorityRecoveryUnavailable,
)
from liquent_platform.persistence.membership_authority_anchor import (
    DatabaseWorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.persistence.membership_authority_recovery import (
    DatabaseOfflineWorkspaceMembershipAuthorityRecovery,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)
from liquent_platform.persistence.oidc_trust_authority_recovery import (
    DatabaseOfflineOidcTrustAuthorityRecovery,
)

TARGET = UserId("recovery-target")
OTHER = UserId("recovery-other")
WORKSPACE = WorkspaceId("recovery-workspace")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'recovery.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _foundation(engine: Engine) -> None:
    with engine.begin() as connection:
        for user in (TARGET, OTHER):
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,'active')"),
                {"user": user.encode()},
            )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": WORKSPACE.encode()},
        )


def _global_closed(engine: Engine) -> OidcTrustAuthoritySetRevisionId:
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities VALUES"
            " (:target,'inactive'),(:other,'active')"
        ), {"target": TARGET.encode(), "other": OTHER.encode()})
    revision = OidcTrustAuthoritySetRevisionId("global-recovery-expected")
    assert DatabaseOidcTrustAuthoritySetAnchor(
        engine, generate_revision_id=lambda: revision
    ).anchor(
        OidcTrustAuthorityLifecycleChangeId("global-recovery-anchor"),
        SessionPrincipal(OTHER),
    )
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE identity_users SET status='inactive' WHERE user_id=:other"),
            {"other": OTHER.encode()},
        )
    return revision


def _workspace_closed(engine: Engine) -> WorkspaceMembershipAuthoritySetRevisionId:
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:target,:workspace,'inactive'),(:other,:workspace,'active')"
        ), {
            "target": TARGET.encode(), "other": OTHER.encode(),
            "workspace": WORKSPACE.encode(),
        })
    revision = WorkspaceMembershipAuthoritySetRevisionId(
        "workspace-recovery-expected"
    )
    assert DatabaseWorkspaceMembershipAuthoritySetAnchor(
        engine, generate_revision_id=lambda: revision
    ).anchor(
        WorkspaceMembershipAuthorityLifecycleChangeId(
            "workspace-recovery-anchor"
        ),
        SessionPrincipal(OTHER), WORKSPACE,
    )
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE identity_users SET status='inactive' WHERE user_id=:other"),
            {"other": OTHER.encode()},
        )
    return revision


def test_global_recovery_reactivates_only_historical_target(engine: Engine) -> None:
    _foundation(engine)
    expected = _global_closed(engine)
    recovery = OidcTrustAuthorityRecoveryId("global-recovery")
    port: OfflineOidcTrustAuthorityRecoveryStore = (
        DatabaseOfflineOidcTrustAuthorityRecovery(
            engine,
            generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                "global-recovered"
            ),
        )
    )

    assert port.recover(recovery, TARGET, expected) == (
        RecoveredOidcTrustAuthoritySet(
            recovery, OidcTrustAuthoritySetRevisionId("global-recovered"), TARGET
        )
    )
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT user_id,status FROM oidc_trust_management_authorities"
            " ORDER BY user_id"
        )).all() == [(OTHER.encode(), "active"), (TARGET.encode(), "active")]
        assert connection.scalar(text(
            "SELECT count(*) FROM oidc_trust_authority_lifecycle_changes"
        )) == 1


def test_workspace_recovery_is_exactly_scope_bound(engine: Engine) -> None:
    _foundation(engine)
    expected = _workspace_closed(engine)
    recovery = WorkspaceMembershipAuthorityRecoveryId("workspace-recovery")
    port: OfflineWorkspaceMembershipAuthorityRecoveryStore = (
        DatabaseOfflineWorkspaceMembershipAuthorityRecovery(
            engine,
            generate_revision_id=lambda: (
                WorkspaceMembershipAuthoritySetRevisionId("workspace-recovered")
            ),
        )
    )

    assert port.recover(recovery, TARGET, WORKSPACE, expected) == (
        RecoveredWorkspaceMembershipAuthoritySet(
            recovery,
            WorkspaceMembershipAuthoritySetRevisionId("workspace-recovered"),
            TARGET, WORKSPACE,
        )
    )
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT user_id,status FROM workspace_membership_management_authorities"
            " WHERE workspace_id=:workspace ORDER BY user_id"
        ), {"workspace": WORKSPACE.encode()}).all() == [
            (OTHER.encode(), "active"), (TARGET.encode(), "active")
        ]


@pytest.mark.parametrize("domain", ["global", "workspace"])
def test_recovery_is_closed_while_any_effective_manager_exists(
    engine: Engine, domain: str
) -> None:
    _foundation(engine)
    if domain == "global":
        expected = _global_closed(engine)
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE identity_users SET status='active' WHERE user_id=:other"),
                {"other": OTHER.encode()},
            )
        outcome = DatabaseOfflineOidcTrustAuthorityRecovery(
            engine,
            generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId("unused"),
        ).recover(OidcTrustAuthorityRecoveryId("closed-global"), TARGET, expected)
    else:
        expected = _workspace_closed(engine)
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE identity_users SET status='active' WHERE user_id=:other"),
                {"other": OTHER.encode()},
            )
        outcome = DatabaseOfflineWorkspaceMembershipAuthorityRecovery(
            engine,
            generate_revision_id=lambda: (
                WorkspaceMembershipAuthoritySetRevisionId("unused")
            ),
        ).recover(
            WorkspaceMembershipAuthorityRecoveryId("closed-workspace"),
            TARGET, WORKSPACE, expected,
        )
    assert outcome is None


@pytest.mark.parametrize("domain", ["global", "workspace"])
def test_inactive_target_user_cannot_be_recovered(
    engine: Engine, domain: str
) -> None:
    _foundation(engine)
    expected = _global_closed(engine) if domain == "global" else _workspace_closed(engine)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE identity_users SET status='inactive' WHERE user_id=:target"),
            {"target": TARGET.encode()},
        )
    if domain == "global":
        outcome = DatabaseOfflineOidcTrustAuthorityRecovery(
            engine,
            generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId("unused"),
        ).recover(OidcTrustAuthorityRecoveryId("inactive-global"), TARGET, expected)
    else:
        outcome = DatabaseOfflineWorkspaceMembershipAuthorityRecovery(
            engine,
            generate_revision_id=lambda: (
                WorkspaceMembershipAuthoritySetRevisionId("unused")
            ),
        ).recover(
            WorkspaceMembershipAuthorityRecoveryId("inactive-workspace"),
            TARGET, WORKSPACE, expected,
        )
    assert outcome is None


def test_global_recovery_can_restore_a_missing_current_pointer(engine: Engine) -> None:
    _foundation(engine)
    expected = _global_closed(engine)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM oidc_trust_authority_current_set"))

    outcome = DatabaseOfflineOidcTrustAuthorityRecovery(
        engine,
        generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
            "restored-pointer"
        ),
    ).recover(
        OidcTrustAuthorityRecoveryId("restore-pointer"), TARGET, expected
    )
    assert outcome is not None


def test_workspace_recovery_can_restore_a_missing_current_pointer(
    engine: Engine,
) -> None:
    _foundation(engine)
    expected = _workspace_closed(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "DELETE FROM workspace_membership_authority_current_sets"
            " WHERE workspace_id=:workspace"
        ), {"workspace": WORKSPACE.encode()})

    outcome = DatabaseOfflineWorkspaceMembershipAuthorityRecovery(
        engine,
        generate_revision_id=lambda: WorkspaceMembershipAuthoritySetRevisionId(
            "restored-workspace-pointer"
        ),
    ).recover(
        WorkspaceMembershipAuthorityRecoveryId("restore-workspace-pointer"),
        TARGET, WORKSPACE, expected,
    )
    assert outcome is not None


def test_exact_global_retry_survives_later_state_change(engine: Engine) -> None:
    _foundation(engine)
    expected = _global_closed(engine)
    recovery = OidcTrustAuthorityRecoveryId("retry-global-recovery")
    store = DatabaseOfflineOidcTrustAuthorityRecovery(
        engine,
        generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
            "retry-global-result"
        ),
    )
    result = store.recover(recovery, TARGET, expected)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE identity_users SET status='inactive' WHERE user_id=:target"),
            {"target": TARGET.encode()},
        )
    assert store.recover(recovery, TARGET, expected) == result


def test_exact_workspace_retry_survives_later_state_change(engine: Engine) -> None:
    _foundation(engine)
    expected = _workspace_closed(engine)
    recovery = WorkspaceMembershipAuthorityRecoveryId("retry-workspace-recovery")
    store = DatabaseOfflineWorkspaceMembershipAuthorityRecovery(
        engine,
        generate_revision_id=lambda: WorkspaceMembershipAuthoritySetRevisionId(
            "retry-workspace-result"
        ),
    )
    result = store.recover(recovery, TARGET, WORKSPACE, expected)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE identity_workspaces SET status='inactive'"),
        )
    assert store.recover(recovery, TARGET, WORKSPACE, expected) == result


@pytest.mark.parametrize("domain", ["global", "workspace"])
def test_recovery_id_reuse_with_different_target_is_conflict(
    engine: Engine, domain: str
) -> None:
    _foundation(engine)
    if domain == "global":
        expected = _global_closed(engine)
        recovery = OidcTrustAuthorityRecoveryId("conflict-global-recovery")
        store = DatabaseOfflineOidcTrustAuthorityRecovery(
            engine,
            generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                "conflict-global-result"
            ),
        )
        assert store.recover(recovery, TARGET, expected)
        with pytest.raises(OidcTrustAuthorityRecoveryConflict):
            store.recover(recovery, OTHER, expected)
    else:
        expected = _workspace_closed(engine)
        recovery = WorkspaceMembershipAuthorityRecoveryId(
            "conflict-workspace-recovery"
        )
        store = DatabaseOfflineWorkspaceMembershipAuthorityRecovery(
            engine,
            generate_revision_id=lambda: (
                WorkspaceMembershipAuthoritySetRevisionId(
                    "conflict-workspace-result"
                )
            ),
        )
        assert store.recover(recovery, TARGET, WORKSPACE, expected)
        with pytest.raises(WorkspaceMembershipAuthorityRecoveryConflict):
            store.recover(recovery, OTHER, WORKSPACE, expected)


@pytest.mark.parametrize("domain", ["global", "workspace"])
def test_unmigrated_store_is_detail_free_unavailable(
    tmp_path: Path, domain: str
) -> None:
    database = build_engine(f"sqlite:///{tmp_path / domain}.db")
    try:
        if domain == "global":
            with pytest.raises(OidcTrustAuthorityRecoveryUnavailable) as raised:
                DatabaseOfflineOidcTrustAuthorityRecovery(
                    database,
                    generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                        "unused"
                    ),
                ).recover(
                    OidcTrustAuthorityRecoveryId("unavailable-global"),
                    TARGET, OidcTrustAuthoritySetRevisionId("expected"),
                )
        else:
            with pytest.raises(
                WorkspaceMembershipAuthorityRecoveryUnavailable
            ) as raised:
                DatabaseOfflineWorkspaceMembershipAuthorityRecovery(
                    database,
                    generate_revision_id=lambda: (
                        WorkspaceMembershipAuthoritySetRevisionId("unused")
                    ),
                ).recover(
                    WorkspaceMembershipAuthorityRecoveryId(
                        "unavailable-workspace"
                    ),
                    TARGET, WORKSPACE,
                    WorkspaceMembershipAuthoritySetRevisionId("expected"),
                )
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
    finally:
        database.dispose()
