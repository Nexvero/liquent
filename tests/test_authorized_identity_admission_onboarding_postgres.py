from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, text

from liquent_platform.application.onboard_identity import (
    AuthorizedIdentityAdmissionOnboarding,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.onboarding import OnboardingDecisionId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_provisioning import (
    DatabaseIdentityAdmissionProvisioningStore,
)
from liquent_platform.persistence.onboarding_decision import (
    DatabaseAuthorizedOnboardingDecisions,
)

pytestmark = pytest.mark.postgres_integration


def test_real_chain_converges_on_one_decision_and_admission(
    postgres_engine: Engine,
) -> None:
    actor = UserId("actor-187")
    target = UserId("target-187")
    workspace = WorkspaceId("workspace-187")
    decision = OnboardingDecisionId("decision-187")
    request = ProvisioningRequestId("request-187")
    admission = IdentityAdmissionId("admission-187")
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO identity_users (user_id, status)"
                " VALUES (:actor, 'active'), (:target, 'active')"
            ),
            {"actor": actor.encode(), "target": target.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO identity_workspaces (workspace_id, status)"
                " VALUES (:workspace, 'active')"
            ),
            {"workspace": workspace.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_onboarding_management"
                " (user_id, workspace_id, status)"
                " VALUES (:actor, :workspace, 'active')"
            ),
            {"actor": actor.encode(), "workspace": workspace.encode()},
        )

    workflow = AuthorizedIdentityAdmissionOnboarding(
        DatabaseAuthorizedOnboardingDecisions(
            postgres_engine,
            generate_provisioning_request_id=lambda: request,
        ),
        DatabaseIdentityAdmissionProvisioningStore(
            postgres_engine,
            now=lambda: datetime(2026, 8, 12, tzinfo=UTC),
            generate_admission_id=lambda: admission,
        ),
        admission_lifetime=timedelta(days=1),
    )

    assert workflow.onboard(
        decision, SessionPrincipal(actor), target, workspace
    ) == admission
    assert workflow.onboard(
        decision, SessionPrincipal(actor), target, workspace
    ) == admission
    with postgres_engine.connect() as connection:
        assert connection.scalar(
            text("SELECT count(*) FROM authorized_onboarding_decisions")
        ) == 1
        assert connection.scalar(text("SELECT count(*) FROM identity_admissions")) == 1
