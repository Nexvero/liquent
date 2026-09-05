from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, text

from liquent_platform.persistence.identity_onboarding_composition import (
    compose_identity_onboarding,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.onboarding import OnboardingDecisionId
from liquent_platform.identity.lifecycle import (
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal

pytestmark = pytest.mark.postgres_integration


class Material:
    def new_user_id(self) -> UserId:
        return UserId("user-188")

    def new_workspace_id(self) -> WorkspaceId:
        return WorkspaceId("workspace-188")

    def new_user_lifecycle_revision_id(self) -> UserLifecycleRevisionId:
        return UserLifecycleRevisionId("user-revision-188")

    def new_workspace_lifecycle_revision_id(
        self,
    ) -> WorkspaceLifecycleRevisionId:
        return WorkspaceLifecycleRevisionId("workspace-revision-188")

    def new_onboarding_decision_id(self) -> OnboardingDecisionId:
        return OnboardingDecisionId("decision-188")

    def new_provisioning_request_id(self) -> ProvisioningRequestId:
        return ProvisioningRequestId("request-188")

    def new_identity_admission_id(self) -> IdentityAdmissionId:
        return IdentityAdmissionId("admission-188")


def test_composed_bootstrap_and_onboarding_chain(postgres_engine: Engine) -> None:
    composition = compose_identity_onboarding(
        postgres_engine,
        admission_lifetime=timedelta(days=1),
        now=lambda: datetime(2026, 8, 12, tzinfo=UTC),
        material=Material(),  # type: ignore[arg-type]
    )
    bootstrap = composition.bootstrap.bootstrap()
    assert bootstrap is not None

    admission = composition.onboarding.onboard(
        composition.new_decision_id(),
        SessionPrincipal(bootstrap.user_id),
        bootstrap.user_id,
        bootstrap.workspace_id,
    )

    assert admission == IdentityAdmissionId("admission-188")
    with postgres_engine.connect() as connection:
        assert connection.scalar(
            text("SELECT count(*) FROM authorized_onboarding_decisions")
        ) == 1
        assert connection.scalar(text("SELECT count(*) FROM identity_admissions")) == 1
