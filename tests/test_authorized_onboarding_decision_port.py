from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import ProvisioningRequestId
from liquent_platform.identity.onboarding import (
    AuthorizedOnboardingDecision,
    OnboardingDecisionId,
)
from liquent_platform.identity.ports import AuthorizedOnboardingDecisionStore
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal


class StubDecisionStore:
    def decide(
        self,
        decision_id: OnboardingDecisionId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
    ) -> AuthorizedOnboardingDecision | None:
        return AuthorizedOnboardingDecision(
            decision_id,
            ProvisioningRequestId("request-1"),
            principal.user_id,
            target_user_id,
            target_workspace_id,
        )


def test_port_has_no_role_capability_or_allow_argument() -> None:
    decision = StubDecisionStore().decide(
        OnboardingDecisionId("decision-1"),
        SessionPrincipal(UserId("actor-1")),
        UserId("target-1"),
        WorkspaceId("workspace-1"),
    )
    assert decision is not None
    assert decision.provisioning_request_id.value == "request-1"
