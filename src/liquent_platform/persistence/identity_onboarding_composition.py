"""Internal production composition for identity-authority onboarding."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from liquent_platform.application.onboard_identity import (
    AuthorizedIdentityAdmissionOnboarding,
)
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.onboarding import OnboardingDecisionId
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.identity_provisioning import (
    DatabaseIdentityAdmissionProvisioningStore,
)
from liquent_platform.persistence.onboarding_decision import (
    DatabaseAuthorizedOnboardingDecisions,
)


@dataclass(frozen=True, slots=True)
class IdentityOnboardingComposition:
    """Internal capabilities; no transport and no ownership of the engine."""

    bootstrap: DatabaseInitialIdentityAuthorityBootstrap
    onboarding: AuthorizedIdentityAdmissionOnboarding
    _material: SecureIdentityAuthorityMaterialGenerator

    def new_decision_id(self) -> OnboardingDecisionId:
        return self._material.new_onboarding_decision_id()

    def __repr__(self) -> str:
        return "IdentityOnboardingComposition()"


def compose_identity_onboarding(
    engine: Engine,
    *,
    admission_lifetime: timedelta,
    now: Callable[[], datetime] | None = None,
    material: SecureIdentityAuthorityMaterialGenerator | None = None,
) -> IdentityOnboardingComposition:
    """Wire the internal chain around one externally owned database engine."""

    source = material or SecureIdentityAuthorityMaterialGenerator()
    clock = now or (lambda: datetime.now(UTC))
    decisions = DatabaseAuthorizedOnboardingDecisions(
        engine,
        generate_provisioning_request_id=source.new_provisioning_request_id,
    )
    admissions = DatabaseIdentityAdmissionProvisioningStore(
        engine,
        now=clock,
        generate_admission_id=source.new_identity_admission_id,
    )
    return IdentityOnboardingComposition(
        bootstrap=DatabaseInitialIdentityAuthorityBootstrap(
            engine,
            generate_user_id=source.new_user_id,
            generate_workspace_id=source.new_workspace_id,
            generate_user_revision_id=source.new_user_lifecycle_revision_id,
            generate_workspace_revision_id=source.new_workspace_lifecycle_revision_id,
        ),
        onboarding=AuthorizedIdentityAdmissionOnboarding(
            decisions,
            admissions,
            admission_lifetime=admission_lifetime,
        ),
        _material=source,
    )
