from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from liquent_platform.persistence.identity_onboarding_composition import (
    IdentityOnboardingComposition,
    compose_identity_onboarding,
)
from liquent_platform.application.onboard_identity import (
    AuthorizedIdentityAdmissionOnboarding,
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
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)


class Material:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def new_user_id(self) -> UserId:
        self.calls.append("user")
        return UserId("user-1")

    def new_workspace_id(self) -> WorkspaceId:
        self.calls.append("workspace")
        return WorkspaceId("workspace-1")

    def new_user_lifecycle_revision_id(self) -> UserLifecycleRevisionId:
        self.calls.append("user-revision")
        return UserLifecycleRevisionId("user-revision-1")

    def new_workspace_lifecycle_revision_id(
        self,
    ) -> WorkspaceLifecycleRevisionId:
        self.calls.append("workspace-revision")
        return WorkspaceLifecycleRevisionId("workspace-revision-1")

    def new_onboarding_decision_id(self) -> OnboardingDecisionId:
        self.calls.append("decision")
        return OnboardingDecisionId("decision-1")

    def new_provisioning_request_id(self) -> ProvisioningRequestId:
        self.calls.append("request")
        return ProvisioningRequestId("request-1")

    def new_identity_admission_id(self) -> IdentityAdmissionId:
        self.calls.append("admission")
        return IdentityAdmissionId("admission-1")


class EngineSentinel:
    def dispose(self) -> None:  # pragma: no cover - must never be called
        raise AssertionError("composition does not own the engine")


def _compose(material: Material | None = None) -> IdentityOnboardingComposition:
    return compose_identity_onboarding(
        EngineSentinel(),  # type: ignore[arg-type]
        admission_lifetime=timedelta(days=1),
        now=lambda: datetime(2026, 8, 12, tzinfo=UTC),
        material=material,  # type: ignore[arg-type]
    )


def test_composition_exposes_only_internal_capabilities() -> None:
    material = Material()
    composition = _compose(material)

    assert isinstance(
        composition.bootstrap, DatabaseInitialIdentityAuthorityBootstrap
    )
    assert isinstance(composition.onboarding, AuthorizedIdentityAdmissionOnboarding)
    assert composition.new_decision_id() == OnboardingDecisionId("decision-1")
    assert material.calls == ["decision"]
    assert repr(composition) == "IdentityOnboardingComposition()"


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(seconds=-1), "day"])
def test_invalid_policy_fails_without_drawing_material(lifetime: Any) -> None:
    material = Material()

    with pytest.raises(ValueError, match="admission lifetime must be positive"):
        compose_identity_onboarding(
            EngineSentinel(),  # type: ignore[arg-type]
            admission_lifetime=lifetime,
            material=material,  # type: ignore[arg-type]
        )
    assert material.calls == []


def test_composition_never_disposes_the_injected_engine() -> None:
    _compose()
