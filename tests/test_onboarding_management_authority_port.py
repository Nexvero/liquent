from liquent_platform.identity.access import UserId
from liquent_platform.identity.ports import OnboardingManagementAuthorityLookup
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal


class StubAuthority:
    def permits_onboarding_management(
        self,
        principal: SessionPrincipal,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
    ) -> bool:
        return (
            principal.user_id == UserId("actor-1")
            and target_user_id == UserId("target-1")
            and target_workspace_id == WorkspaceId("workspace-1")
        )


def _decide(port: OnboardingManagementAuthorityLookup) -> bool:
    return port.permits_onboarding_management(
        SessionPrincipal(UserId("actor-1")),
        UserId("target-1"),
        WorkspaceId("workspace-1"),
    )


def test_port_is_structural_without_a_role_or_allow_argument() -> None:
    assert _decide(StubAuthority()) is True
