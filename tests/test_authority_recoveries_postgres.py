from __future__ import annotations

import threading

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityRecoveryId,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityRecoveryId,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.membership_authority_anchor import (
    DatabaseWorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.persistence.membership_authority_recovery import (
    DatabaseOfflineWorkspaceMembershipAuthorityRecovery,
)
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)
from liquent_platform.persistence.oidc_trust_authority_recovery import (
    DatabaseOfflineOidcTrustAuthorityRecovery,
)

pytestmark = pytest.mark.postgres_integration


def _concurrent(attempts) -> list[object]:
    start = threading.Barrier(2)
    guard = threading.Lock()
    outcomes: list[object] = []

    def run(attempt) -> None:
        try:
            start.wait(timeout=15)
            outcome: object = attempt()
        except Exception as error:
            outcome = error
        with guard:
            outcomes.append(outcome)

    threads = [threading.Thread(target=run, args=(attempt,)) for attempt in attempts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert [thread.is_alive() for thread in threads] == [False, False]
    return outcomes


def test_concurrent_global_recoveries_have_one_success(
    postgres_engine: Engine, postgres_url: str
) -> None:
    target = UserId("recovery-216-global-target")
    former = UserId("recovery-216-global-former")
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES"
            " (:target,'active'),(:former,'active')"
        ), {"target": target.encode(), "former": former.encode()})
        connection.execute(text(
            "INSERT INTO oidc_trust_management_authorities VALUES"
            " (:target,'inactive'),(:former,'active')"
        ), {"target": target.encode(), "former": former.encode()})
    expected = OidcTrustAuthoritySetRevisionId("recovery-216-global-expected")
    assert DatabaseOidcTrustAuthoritySetAnchor(
        postgres_engine, generate_revision_id=lambda: expected
    ).anchor(
        OidcTrustAuthorityLifecycleChangeId("recovery-216-global-anchor"),
        SessionPrincipal(former),
    )
    with postgres_engine.begin() as connection:
        connection.execute(
            text("UPDATE identity_users SET status='inactive' WHERE user_id=:former"),
            {"former": former.encode()},
        )
    engines = [build_engine(postgres_url) for _ in range(2)]
    try:
        attempts = [
            lambda index=index: DatabaseOfflineOidcTrustAuthorityRecovery(
                engines[index],
                generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                    f"recovery-216-global-result-{index}"
                ),
            ).recover(
                OidcTrustAuthorityRecoveryId(
                    f"recovery-216-global-id-{index}"
                ),
                target, expected,
            )
            for index in range(2)
        ]
        outcomes = _concurrent(attempts)
    finally:
        for engine in engines:
            engine.dispose()
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
    assert sum(outcome is not None for outcome in outcomes) == 1


def test_concurrent_workspace_recoveries_have_one_success(
    postgres_engine: Engine, postgres_url: str
) -> None:
    target = UserId("recovery-216-workspace-target")
    former = UserId("recovery-216-workspace-former")
    workspace = WorkspaceId("recovery-216-workspace")
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES"
            " (:target,'active'),(:former,'active')"
        ), {"target": target.encode(), "former": former.encode()})
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": workspace.encode()},
        )
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:target,:workspace,'inactive'),(:former,:workspace,'active')"
        ), {
            "target": target.encode(), "former": former.encode(),
            "workspace": workspace.encode(),
        })
    expected = WorkspaceMembershipAuthoritySetRevisionId(
        "recovery-216-workspace-expected"
    )
    assert DatabaseWorkspaceMembershipAuthoritySetAnchor(
        postgres_engine, generate_revision_id=lambda: expected
    ).anchor(
        WorkspaceMembershipAuthorityLifecycleChangeId(
            "recovery-216-workspace-anchor"
        ),
        SessionPrincipal(former), workspace,
    )
    with postgres_engine.begin() as connection:
        connection.execute(
            text("UPDATE identity_users SET status='inactive' WHERE user_id=:former"),
            {"former": former.encode()},
        )
    engines = [build_engine(postgres_url) for _ in range(2)]
    try:
        attempts = [
            lambda index=index: (
                DatabaseOfflineWorkspaceMembershipAuthorityRecovery(
                    engines[index],
                    generate_revision_id=lambda: (
                        WorkspaceMembershipAuthoritySetRevisionId(
                            f"recovery-216-workspace-result-{index}"
                        )
                    ),
                ).recover(
                    WorkspaceMembershipAuthorityRecoveryId(
                        f"recovery-216-workspace-id-{index}"
                    ),
                    target, workspace, expected,
                )
            )
            for index in range(2)
        ]
        outcomes = _concurrent(attempts)
    finally:
        for engine in engines:
            engine.dispose()
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
    assert sum(outcome is not None for outcome in outcomes) == 1
