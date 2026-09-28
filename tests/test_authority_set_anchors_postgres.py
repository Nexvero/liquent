from __future__ import annotations

import threading

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.membership_authority_anchor import (
    DatabaseWorkspaceMembershipAuthoritySetAnchor,
)
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)

pytestmark = pytest.mark.postgres_integration


def test_concurrent_exact_global_anchor_retries_converge(
    postgres_engine: Engine, postgres_url: str
) -> None:
    actor = UserId("anchor-213-global")
    with postgres_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:actor,'active')"),
            {"actor": actor.encode()},
        )
        connection.execute(
            text("INSERT INTO oidc_trust_management_authorities VALUES"
                 " (:actor,'active')"),
            {"actor": actor.encode()},
        )
    change = OidcTrustAuthorityLifecycleChangeId("anchor-213-global-change")
    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(index: int) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseOidcTrustAuthoritySetAnchor(
                engine,
                generate_revision_id=lambda: OidcTrustAuthoritySetRevisionId(
                    f"anchor-213-global-revision-{index}"
                ),
            )
            start.wait(timeout=15)
            outcome: object = store.anchor(change, SessionPrincipal(actor))
        except Exception as error:
            outcome = error
        finally:
            engine.dispose()
        with guard:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
    assert len(outcomes) == 2
    assert outcomes[0] == outcomes[1]


def test_concurrent_workspace_anchors_have_one_decision(
    postgres_engine: Engine, postgres_url: str
) -> None:
    actor = UserId("anchor-213-membership")
    workspace = WorkspaceId("anchor-213-workspace")
    with postgres_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:actor,'active')"),
            {"actor": actor.encode()},
        )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": workspace.encode()},
        )
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES"
            " (:actor,:workspace,'active')"
        ), {"actor": actor.encode(), "workspace": workspace.encode()})
    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(index: int) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseWorkspaceMembershipAuthoritySetAnchor(
                engine,
                generate_revision_id=lambda: (
                    WorkspaceMembershipAuthoritySetRevisionId(
                        f"anchor-213-membership-revision-{index}"
                    )
                ),
            )
            start.wait(timeout=15)
            outcome: object = store.anchor(
                WorkspaceMembershipAuthorityLifecycleChangeId(
                    f"anchor-213-membership-change-{index}"
                ),
                SessionPrincipal(actor),
                workspace,
            )
        except Exception as error:
            outcome = error
        finally:
            engine.dispose()
        with guard:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(outcome is not None for outcome in outcomes) == 1
