from datetime import timedelta
from typing import Any

import pytest

from liquent_platform.application.onboard_identity import (
    AuthorizedIdentityAdmissionOnboarding,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.onboarding import (
    AuthorizedOnboardingDecision,
    OnboardingDecisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    IdentityAdmissionStoreUnavailable,
    OnboardingDecisionStoreUnavailable,
)

DECISION_ID = OnboardingDecisionId("decision-1")
REQUEST_ID = ProvisioningRequestId("request-1")
ACTOR = UserId("actor-1")
TARGET = UserId("target-1")
WORKSPACE = WorkspaceId("workspace-1")
LIFETIME = timedelta(hours=24)
DECISION = AuthorizedOnboardingDecision(
    DECISION_ID, REQUEST_ID, ACTOR, TARGET, WORKSPACE
)


class DecisionStore:
    def __init__(self, result: Any = DECISION) -> None:
        self.result = result
        self.calls: list[tuple[Any, ...]] = []

    def decide(self, *args: Any) -> AuthorizedOnboardingDecision | None:
        self.calls.append(args)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class AdmissionStore:
    def __init__(self, result: Any = IdentityAdmissionId("admission-1")) -> None:
        self.result = result
        self.calls: list[tuple[Any, ...]] = []

    def provision_admission(self, *args: Any) -> IdentityAdmissionId:
        self.calls.append(args)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _workflow(
    decisions: DecisionStore, admissions: AdmissionStore
) -> AuthorizedIdentityAdmissionOnboarding:
    return AuthorizedIdentityAdmissionOnboarding(
        decisions, admissions, admission_lifetime=LIFETIME
    )


def _onboard(workflow: AuthorizedIdentityAdmissionOnboarding):
    return workflow.onboard(
        DECISION_ID, SessionPrincipal(ACTOR), TARGET, WORKSPACE
    )


def test_provisions_only_with_values_returned_by_persistent_decision() -> None:
    returned = AuthorizedOnboardingDecision(
        DECISION_ID,
        ProvisioningRequestId("stored-request"),
        ACTOR,
        UserId("stored-target"),
        WorkspaceId("stored-workspace"),
    )
    decisions = DecisionStore(returned)
    admissions = AdmissionStore()

    assert _onboard(_workflow(decisions, admissions)) == IdentityAdmissionId(
        "admission-1"
    )
    assert decisions.calls == [
        (DECISION_ID, SessionPrincipal(ACTOR), TARGET, WORKSPACE)
    ]
    assert admissions.calls == [
        (
            ProvisioningRequestId("stored-request"),
            UserId("stored-target"),
            WorkspaceId("stored-workspace"),
            LIFETIME,
        )
    ]


def test_neutral_decision_rejection_never_reaches_provisioning() -> None:
    decisions = DecisionStore(None)
    admissions = AdmissionStore()

    assert _onboard(_workflow(decisions, admissions)) is None
    assert admissions.calls == []


@pytest.mark.parametrize(
    "failure",
    [OnboardingDecisionStoreUnavailable(), IdentityAdmissionStoreUnavailable()],
)
def test_dependency_failure_propagates_without_retry(failure: Exception) -> None:
    decisions = DecisionStore(
        failure if isinstance(failure, OnboardingDecisionStoreUnavailable) else DECISION
    )
    admissions = AdmissionStore(failure)

    with pytest.raises(type(failure)) as raised:
        _onboard(_workflow(decisions, admissions))

    assert raised.value is failure
    assert len(decisions.calls) == 1
    assert len(admissions.calls) == (
        0 if isinstance(failure, OnboardingDecisionStoreUnavailable) else 1
    )


def test_exact_repeat_reuses_policy_and_dependency_handles() -> None:
    decisions = DecisionStore()
    admissions = AdmissionStore()
    workflow = _workflow(decisions, admissions)

    assert _onboard(workflow) == _onboard(workflow)
    assert len(decisions.calls) == 2
    assert admissions.calls[0] == admissions.calls[1]


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(seconds=-1), "1 day"])
def test_invalid_policy_is_rejected_before_dependencies(lifetime: Any) -> None:
    decisions = DecisionStore()
    admissions = AdmissionStore()

    with pytest.raises(ValueError, match="admission lifetime must be positive"):
        AuthorizedIdentityAdmissionOnboarding(
            decisions, admissions, admission_lifetime=lifetime
        )
    assert decisions.calls == admissions.calls == []


def test_repr_contains_no_dependency_or_policy_detail() -> None:
    workflow = _workflow(DecisionStore(), AdmissionStore())

    assert repr(workflow) == "AuthorizedIdentityAdmissionOnboarding()"
