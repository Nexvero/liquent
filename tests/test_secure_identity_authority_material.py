from typing import Any

import pytest

from liquent_platform.identity import authority_material
from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.authority_material import (
    MINIMUM_AUTHORITY_ENTROPY_BYTES,
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.onboarding import OnboardingDecisionId
from liquent_platform.identity.research import WorkspaceId


def test_all_identifier_kinds_use_independent_secure_draws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(["user", "workspace", "decision", "request", "admission"])
    calls: list[int] = []

    def draw(entropy_bytes: int) -> str:
        calls.append(entropy_bytes)
        return next(values)

    monkeypatch.setattr(authority_material.secrets, "token_urlsafe", draw)
    generator = SecureIdentityAuthorityMaterialGenerator()

    assert generator.new_user_id() == UserId("user")
    assert generator.new_workspace_id() == WorkspaceId("workspace")
    assert generator.new_onboarding_decision_id() == OnboardingDecisionId("decision")
    assert generator.new_provisioning_request_id() == ProvisioningRequestId("request")
    assert generator.new_identity_admission_id() == IdentityAdmissionId("admission")
    assert calls == [MINIMUM_AUTHORITY_ENTROPY_BYTES] * 5
    assert repr(generator) == "SecureIdentityAuthorityMaterialGenerator()"


@pytest.mark.parametrize("entropy", [0, 31, True, 32.0])
def test_weak_or_invalid_entropy_is_rejected(entropy: Any) -> None:
    with pytest.raises(
        ValueError, match="identity authority entropy must be at least 32 bytes"
    ):
        SecureIdentityAuthorityMaterialGenerator(entropy)
