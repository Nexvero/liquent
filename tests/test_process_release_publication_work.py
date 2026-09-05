import pytest

from liquent_platform.application.process_release_publication_work import (
    ProcessReleasePublicationWork,
    ReleasePublicationWorkUnavailable,
)
from liquent_platform.identity.release_publication import (
    FinalizedReleasePublication,
    FinalizedReleasePublicationRecovery,
    PreparedReleasePublicationAttempt,
    ReleasePublicationAttemptId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationFinalStatus,
    ReleasePublicationHandoffId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationReconciliationKind,
    ReleasePublicationRecoveryId,
    ReleasePublicationWorkRequest,
    ReleasePublicationWorkResultKind,
    ReleasePublicationWorkState,
    ReleasePublicationWorkStateKind,
    ReleasePublicationWritePendingReconciliation,
    ReleasePublisherAuthorityId,
)


EXECUTION = ReleasePublicationExecutionId("execution-lq271")
HANDOFF = ReleasePublicationHandoffId("handoff-lq271")
ATTEMPT_ONE = ReleasePublicationAttemptId("attempt-lq271-one")
ATTEMPT_TWO = ReleasePublicationAttemptId("attempt-lq271-two")
REQUEST = ReleasePublicationWorkRequest(
    EXECUTION,
    HANDOFF,
    ReleasePublisherAuthorityId("publisher-lq271"),
    ReleasePublicationChannelId("channel-lq271"),
    ReleasePublicationChannelPolicyRevisionId("revision-lq271"),
)


class Dependencies:
    def __init__(self, state=None, finalized=None):
        self.state = state
        self.finalized = finalized
        self.calls = []

    def get_work_state(self, request):
        self.calls.append(("state", request))
        return self.state

    def prepare_attempt(self, *values):
        self.calls.append(("prepare-one", values))
        return PreparedReleasePublicationAttempt(EXECUTION, ATTEMPT_ONE, HANDOFF, 1)

    def create_publication(self, execution_id, attempt_id):
        self.calls.append(("create-one", execution_id, attempt_id))
        return ReleasePublicationWritePendingReconciliation(
            execution_id, attempt_id, HANDOFF
        )

    def prepare_retry_attempt(self, execution_id, recovered_attempt_id):
        self.calls.append(("prepare-two", execution_id, recovered_attempt_id))
        return PreparedReleasePublicationAttempt(EXECUTION, ATTEMPT_TWO, HANDOFF, 2)

    def create_retry_publication(self, execution_id, attempt_id):
        self.calls.append(("create-two", execution_id, attempt_id))
        return ReleasePublicationWritePendingReconciliation(
            execution_id, attempt_id, HANDOFF
        )

    def finalize_current_outcome(self, execution_id, attempt_id):
        self.calls.append(("finalize", execution_id, attempt_id))
        return self.finalized


def _worker(dependencies):
    return ProcessReleasePublicationWork(
        states=dependencies,
        attempt_one=dependencies,
        create_one=dependencies,
        attempt_two=dependencies,
        create_two=dependencies,
        finalizer=dependencies,
    )


def test_new_work_prepares_creates_once_and_reconciles_once() -> None:
    dependencies = Dependencies()
    result = _worker(dependencies).process(REQUEST)
    assert result.kind is ReleasePublicationWorkResultKind.PENDING_RECONCILIATION
    assert [call[0] for call in dependencies.calls] == [
        "state", "prepare-one", "create-one", "finalize"
    ]


def test_unknown_attempt_is_only_finalized_and_never_created() -> None:
    dependencies = Dependencies(ReleasePublicationWorkState(
        ReleasePublicationWorkStateKind.ATTEMPT_ONE_UNKNOWN, ATTEMPT_ONE
    ))
    result = _worker(dependencies).process(REQUEST)
    assert result.kind is ReleasePublicationWorkResultKind.PENDING_RECONCILIATION
    assert [call[0] for call in dependencies.calls] == ["state", "finalize"]


def test_recovered_absence_prepares_attempt_two_and_creates_once() -> None:
    dependencies = Dependencies(ReleasePublicationWorkState(
        ReleasePublicationWorkStateKind.ATTEMPT_ONE_ABSENCE_RECOVERED,
        ATTEMPT_ONE,
    ))
    result = _worker(dependencies).process(REQUEST)
    assert result.kind is ReleasePublicationWorkResultKind.PENDING_RECONCILIATION
    assert [call[0] for call in dependencies.calls] == [
        "state", "prepare-two", "create-two", "finalize"
    ]


def test_prepared_attempt_two_does_not_run_a_preflight_or_first_creator() -> None:
    dependencies = Dependencies(ReleasePublicationWorkState(
        ReleasePublicationWorkStateKind.ATTEMPT_TWO_PREPARED, ATTEMPT_TWO
    ))
    _worker(dependencies).process(REQUEST)
    assert [call[0] for call in dependencies.calls] == [
        "state", "create-two", "finalize"
    ]


@pytest.mark.parametrize(
    ("finalized", "expected"),
    [
        (
            FinalizedReleasePublication(
                ReleasePublicationProviderReceiptId("receipt-lq271"),
                EXECUTION, ATTEMPT_ONE, HANDOFF,
                ReleasePublicationFinalStatus.PUBLISHED,
            ),
            ReleasePublicationWorkResultKind.PUBLISHED,
        ),
        (
            FinalizedReleasePublication(
                ReleasePublicationProviderReceiptId("receipt-lq271-review"),
                EXECUTION, ATTEMPT_ONE, HANDOFF,
                ReleasePublicationFinalStatus.PUBLISHED_REASSESSMENT_REQUIRED,
                ReleasePublicationReassessmentId("reassessment-lq271"),
            ),
            ReleasePublicationWorkResultKind.PUBLISHED_REASSESSMENT_REQUIRED,
        ),
        (
            FinalizedReleasePublicationRecovery(
                ReleasePublicationRecoveryId("recovery-lq271-conflict"),
                EXECUTION, ATTEMPT_ONE, HANDOFF,
                ReleasePublicationReconciliationKind.CONFLICT,
                False,
                ReleasePublicationReassessmentId("reassessment-lq271-conflict"),
            ),
            ReleasePublicationWorkResultKind.PUBLICATION_CONFLICT,
        ),
        (
            FinalizedReleasePublicationRecovery(
                ReleasePublicationRecoveryId("recovery-lq271-absence"),
                EXECUTION, ATTEMPT_ONE, HANDOFF,
                ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED,
                True,
            ),
            ReleasePublicationWorkResultKind.NOT_ACTIONABLE,
        ),
    ],
)
def test_finalized_outcome_is_mapped_without_sensitive_detail(
    finalized, expected
) -> None:
    dependencies = Dependencies(
        ReleasePublicationWorkState(
            ReleasePublicationWorkStateKind.ATTEMPT_ONE_UNKNOWN, ATTEMPT_ONE
        ),
        finalized,
    )
    result = _worker(dependencies).process(REQUEST)
    assert result.kind is expected
    assert repr(result) == f"ReleasePublicationWorkResult(kind={expected!r})"
    assert "receipt-lq271" not in repr(result)


def test_attempt_two_absence_is_terminal_not_published() -> None:
    finalized = FinalizedReleasePublicationRecovery(
        ReleasePublicationRecoveryId("recovery-lq271-two"),
        EXECUTION, ATTEMPT_TWO, HANDOFF,
        ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED,
        False,
    )
    dependencies = Dependencies(
        ReleasePublicationWorkState(
            ReleasePublicationWorkStateKind.ATTEMPT_TWO_UNKNOWN, ATTEMPT_TWO
        ),
        finalized,
    )
    assert _worker(dependencies).process(REQUEST).kind is (
        ReleasePublicationWorkResultKind.NOT_PUBLISHED
    )


def test_terminal_state_returns_exact_family_without_other_dependency() -> None:
    dependencies = Dependencies(ReleasePublicationWorkState(
        ReleasePublicationWorkStateKind.TERMINAL,
        terminal_result=ReleasePublicationWorkResultKind.PUBLISHED,
    ))
    assert _worker(dependencies).process(REQUEST).kind is (
        ReleasePublicationWorkResultKind.PUBLISHED
    )
    assert [call[0] for call in dependencies.calls] == ["state"]


def test_neutral_preflight_stops_before_create() -> None:
    dependencies = Dependencies()
    dependencies.prepare_attempt = lambda *values: None
    result = _worker(dependencies).process(REQUEST)
    assert result.kind is ReleasePublicationWorkResultKind.NOT_ACTIONABLE
    assert [call[0] for call in dependencies.calls] == ["state"]


def test_malformed_dependency_result_and_fault_are_detail_free() -> None:
    dependencies = Dependencies(state="provider-secret-state")
    with pytest.raises(ReleasePublicationWorkUnavailable) as caught:
        _worker(dependencies).process(REQUEST)
    assert str(caught.value) == "release_publication_work_unavailable"
    assert "provider-secret-state" not in repr(caught.value)


def test_request_and_state_models_reject_open_or_inconsistent_values() -> None:
    with pytest.raises(ReleasePublicationWorkUnavailable):
        _worker(Dependencies()).process(object())
    with pytest.raises(ValueError):
        ReleasePublicationWorkState(
            ReleasePublicationWorkStateKind.ATTEMPT_ONE_UNKNOWN
        )
    with pytest.raises(ValueError):
        ReleasePublicationWorkState(
            ReleasePublicationWorkStateKind.TERMINAL,
            ATTEMPT_ONE,
            ReleasePublicationWorkResultKind.PUBLISHED,
        )
