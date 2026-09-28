"""Authorize one onboarding decision and provision its identity admission."""

from __future__ import annotations

from datetime import timedelta

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.onboarding import OnboardingDecisionId
from liquent_platform.identity.ports import (
    AuthorizedOnboardingDecisionStore,
    IdentityAdmissionProvisioningStore,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal


class AuthorizedIdentityAdmissionOnboarding:
    """Bridge a persistent authorized decision to admission provisioning."""

    __slots__ = ("_admissions", "_decisions", "_lifetime")

    def __init__(
        self,
        decisions: AuthorizedOnboardingDecisionStore,
        admissions: IdentityAdmissionProvisioningStore,
        *,
        admission_lifetime: timedelta,
    ) -> None:
        if (
            type(admission_lifetime) is not timedelta
            or admission_lifetime <= timedelta(0)
        ):
            raise ValueError("admission lifetime must be positive")
        self._decisions = decisions
        self._admissions = admissions
        self._lifetime = admission_lifetime

    def __repr__(self) -> str:
        return "AuthorizedIdentityAdmissionOnboarding()"

    def onboard(
        self,
        decision_id: OnboardingDecisionId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
    ) -> IdentityAdmissionId | None:
        """Provision only from the exact decision returned by the authority store."""

        decision = self._decisions.decide(
            decision_id,
            principal,
            target_user_id,
            target_workspace_id,
        )
        if decision is None:
            return None
        return self._admissions.provision_admission(
            decision.provisioning_request_id,
            decision.target_user_id,
            decision.target_workspace_id,
            self._lifetime,
        )
