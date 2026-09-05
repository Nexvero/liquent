from __future__ import annotations

import threading

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import ProvisioningRequestId
from liquent_platform.identity.onboarding import OnboardingDecisionId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.onboarding_decision import (
    DatabaseAuthorizedOnboardingDecisions,
)

pytestmark = pytest.mark.postgres_integration

ACTOR = UserId("actor-186")
TARGET = UserId("target-186")
WORKSPACE = WorkspaceId("workspace-186")
DECISION = OnboardingDecisionId("decision-186")


def _foundation(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO identity_users (user_id, status)"
                " VALUES (:actor, 'active'), (:target, 'active')"
            ),
            {"actor": ACTOR.encode(), "target": TARGET.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO identity_workspaces (workspace_id, status)"
                " VALUES (:workspace, 'active')"
            ),
            {"workspace": WORKSPACE.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_onboarding_management"
                " (user_id, workspace_id, status)"
                " VALUES (:actor, :workspace, 'active')"
            ),
            {"actor": ACTOR.encode(), "workspace": WORKSPACE.encode()},
        )


def test_concurrent_exact_decision_converges_on_one_request(
    postgres_engine: Engine, postgres_url: str
) -> None:
    _foundation(postgres_engine)
    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(name: str) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseAuthorizedOnboardingDecisions(
                engine,
                generate_provisioning_request_id=lambda: ProvisioningRequestId(
                    f"request-{name}"
                ),
            )
            start.wait(timeout=15)
            outcome: object = store.decide(
                DECISION, SessionPrincipal(ACTOR), TARGET, WORKSPACE
            )
        except Exception as error:
            outcome = error
        finally:
            engine.dispose()
        with guard:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
    requests = {
        outcome.provisioning_request_id
        for outcome in outcomes  # type: ignore[union-attr]
    }
    assert len(requests) == 1
    with postgres_engine.connect() as connection:
        assert connection.scalar(
            text("SELECT count(*) FROM authorized_onboarding_decisions")
        ) == 1
