"""Immutable identities and result of one authorized onboarding decision."""

from dataclasses import dataclass, field

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import ProvisioningRequestId
from liquent_platform.identity.research import WorkspaceId


@dataclass(frozen=True, slots=True)
class OnboardingDecisionId:
    """Internal repetition identity; presenting it grants no authority."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str or not self.value:
            raise ValueError("invalid onboarding decision id")


@dataclass(frozen=True, slots=True)
class AuthorizedOnboardingDecision:
    """One committed decision and its stable admission-provisioning handle."""

    decision_id: OnboardingDecisionId = field(repr=False)
    provisioning_request_id: ProvisioningRequestId = field(repr=False)
    actor_user_id: UserId
    target_user_id: UserId
    target_workspace_id: WorkspaceId
