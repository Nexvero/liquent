from __future__ import annotations

import threading

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityLifecycleIntent,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityLifecycleIntent,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.membership_authority_anchor import (
    DatabaseWorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.persistence.membership_authority_lifecycle import (
    DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle,
)
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)
from liquent_platform.persistence.oidc_trust_authority_lifecycle import (
    DatabaseAuthorizedOidcTrustAuthorityLifecycle,
)

pytestmark = pytest.mark.postgres_integration


def _run_concurrently(attempts, outcomes: list[object]) -> None:
    start = threading.Barrier(2)
    guard = threading.Lock()

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


def test_concurrent_global_grants_from_one_revision_have_one_success(
    postgres_engine: Engine, postgres_url: str
) -> None:
    actor = UserId("lifecycle-214-global-actor")
    targets = (UserId("lifecycle-214-global-a"), UserId("lifecycle-214-global-b"))
    with postgres_engine.begin() as connection:
        for user in (actor, *targets):
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,'active')"),
                {"user": user.encode()},
            )
        connection.execute(
            text("INSERT INTO oidc_trust_management_authorities VALUES"
                 " (:actor,'active')"),
            {"actor": actor.encode()},
        )
    expected = OidcTrustAuthoritySetRevisionId("lifecycle-214-global-anchor")
    assert DatabaseOidcTrustAuthoritySetAnchor(
        postgres_engine, generate_revision_id=lambda: expected
    ).anchor(
        OidcTrustAuthorityLifecycleChangeId("lifecycle-214-global-anchor-change"),
        SessionPrincipal(actor),
    )
    engines = [build_engine(postgres_url) for _ in range(2)]
    try:
        attempts = [
            lambda index=index: DatabaseAuthorizedOidcTrustAuthorityLifecycle(
                engines[index],
                generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                    f"lifecycle-214-global-result-{index}"
                ),
            ).change_authority(
                OidcTrustAuthorityLifecycleChangeId(
                    f"lifecycle-214-global-change-{index}"
                ),
                SessionPrincipal(actor), targets[index],
                OidcTrustAuthorityLifecycleIntent.GRANT, expected,
            )
            for index in range(2)
        ]
        outcomes: list[object] = []
        _run_concurrently(attempts, outcomes)
    finally:
        for engine in engines:
            engine.dispose()
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(outcome is not None for outcome in outcomes) == 1


def test_concurrent_workspace_grants_from_one_revision_have_one_success(
    postgres_engine: Engine, postgres_url: str
) -> None:
    actor = UserId("lifecycle-214-workspace-actor")
    targets = (
        UserId("lifecycle-214-workspace-a"),
        UserId("lifecycle-214-workspace-b"),
    )
    workspace = WorkspaceId("lifecycle-214-workspace")
    with postgres_engine.begin() as connection:
        for user in (actor, *targets):
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,'active')"),
                {"user": user.encode()},
            )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": workspace.encode()},
        )
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:actor,:workspace,'active')"
        ), {"actor": actor.encode(), "workspace": workspace.encode()})
    expected = WorkspaceMembershipAuthoritySetRevisionId(
        "lifecycle-214-workspace-anchor"
    )
    assert DatabaseWorkspaceMembershipAuthoritySetAnchor(
        postgres_engine, generate_revision_id=lambda: expected
    ).anchor(
        WorkspaceMembershipAuthorityLifecycleChangeId(
            "lifecycle-214-workspace-anchor-change"
        ),
        SessionPrincipal(actor), workspace,
    )
    engines = [build_engine(postgres_url) for _ in range(2)]
    try:
        attempts = [
            lambda index=index: (
                DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle(
                    engines[index],
                    generate_revision_id=lambda: (
                        WorkspaceMembershipAuthoritySetRevisionId(
                            f"lifecycle-214-workspace-result-{index}"
                        )
                    ),
                ).change_authority(
                    WorkspaceMembershipAuthorityLifecycleChangeId(
                        f"lifecycle-214-workspace-change-{index}"
                    ),
                    SessionPrincipal(actor), targets[index], workspace,
                    WorkspaceMembershipAuthorityLifecycleIntent.GRANT, expected,
                )
            )
            for index in range(2)
        ]
        outcomes: list[object] = []
        _run_concurrently(attempts, outcomes)
    finally:
        for engine in engines:
            engine.dispose()
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(outcome is not None for outcome in outcomes) == 1
