from datetime import datetime, timezone

from liquent_platform.identity.release_publication import (
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
    ReleasePublicationWorkRequest,
    ReleasePublicationWorkResultKind,
    ReleasePublicationWorkStateKind,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.release_publication_finalize import (
    DatabaseReleasePublicationReconciliationFinalizer,
)
from liquent_platform.persistence.release_publication_reconciliation import (
    DatabaseReleasePublicationUnknownOutcomeReconciliation,
)
from liquent_platform.persistence.release_publication_recovery import (
    DatabaseReleasePublicationRecoveryFinalizer,
)
from liquent_platform.persistence.release_publication_work import (
    DatabaseReleasePublicationCurrentOutcomeFinalizer,
    DatabaseReleasePublicationWorkStateLookup,
)
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, ready
from test_release_publication_reconciliation import observed, unknown
from test_release_publication_target import Inspector


NOW = datetime(2026, 8, 19, 12, tzinfo=timezone.utc)


def _bound_request(ready):
    from sqlalchemy import text

    with ready[0].connect() as connection:
        row = connection.execute(text(
            "SELECT execution.handoff_id,execution.publisher_authority_id,"
            " execution.channel_id,execution.channel_revision_id"
            " FROM release_publication_executions execution"
        )).one()
    from liquent_platform.identity.release_publication import (
        ReleasePublicationHandoffId,
    )

    return ReleasePublicationWorkRequest(
        EXECUTION,
        ReleasePublicationHandoffId(bytes(row.handoff_id).decode()),
        ReleasePublisherAuthorityId(bytes(row.publisher_authority_id).decode()),
        ReleasePublicationChannelId(bytes(row.channel_id).decode()),
        ReleasePublicationChannelPolicyRevisionId(
            bytes(row.channel_revision_id).decode()
        ),
    )


def test_state_lookup_resolves_prepared_attempt(ready):
    prepared = DatabaseReleasePublicationWorkStateLookup(ready[0]).get_work_state(
        _bound_request(ready)
    )
    assert prepared.kind is ReleasePublicationWorkStateKind.ATTEMPT_ONE_PREPARED
    assert prepared.attempt_id == ATTEMPT


def test_state_lookup_resolves_unknown_attempt(unknown):
    unresolved = DatabaseReleasePublicationWorkStateLookup(
        unknown[0]
    ).get_work_state(_bound_request(unknown))
    assert unresolved.kind is ReleasePublicationWorkStateKind.ATTEMPT_ONE_UNKNOWN
    assert unresolved.attempt_id == ATTEMPT


def test_state_lookup_is_neutral_for_missing_or_mismatched_binding(ready):
    lookup = DatabaseReleasePublicationWorkStateLookup(ready[0])
    request = _bound_request(ready)
    missing = ReleasePublicationWorkRequest(
        type(EXECUTION)("missing-lq272"),
        request.handoff_id,
        request.publisher_authority_id,
        request.channel_id,
        request.expected_channel_revision,
    )
    assert lookup.get_work_state(missing) is None
    mismatched = ReleasePublicationWorkRequest(
        EXECUTION,
        request.handoff_id,
        request.publisher_authority_id,
        ReleasePublicationChannelId("other-channel-lq272"),
        request.expected_channel_revision,
    )
    assert lookup.get_work_state(mismatched).kind is (
        ReleasePublicationWorkStateKind.NOT_ACTIONABLE
    )


class CountingInspector(Inspector):
    def __init__(self, result=None):
        super().__init__(result)
        self.count = 0

    def inspect_target(self, target):
        self.count += 1
        return super().inspect_target(target)


def _current(unknown, inspector):
    reconciliation = DatabaseReleasePublicationUnknownOutcomeReconciliation(
        unknown[0], target_inspector=inspector
    )
    receipt = DatabaseReleasePublicationReconciliationFinalizer(
        unknown[0],
        reconciliation=reconciliation,
        generate_receipt_id=lambda: ReleasePublicationProviderReceiptId(
            "receipt-lq272"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "reassessment-lq272-receipt"
        ),
        clock=lambda: NOW,
    )
    recovery = DatabaseReleasePublicationRecoveryFinalizer(
        unknown[0],
        reconciliation=reconciliation,
        generate_recovery_id=lambda: ReleasePublicationRecoveryId(
            "recovery-lq272"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "reassessment-lq272-recovery"
        ),
        clock=lambda: NOW,
    )
    return DatabaseReleasePublicationCurrentOutcomeFinalizer(
        reconciliation=reconciliation,
        receipt_finalizer=receipt,
        recovery_finalizer=recovery,
    )


def test_current_outcome_inspects_once_and_commits_published(unknown):
    inspector = CountingInspector(observed(unknown))
    result = _current(unknown, inspector).finalize_current_outcome(
        EXECUTION, ATTEMPT
    )
    assert inspector.count == 1
    assert result.status.value == "published"
    state = DatabaseReleasePublicationWorkStateLookup(
        unknown[0]
    ).get_work_state(_bound_request(unknown))
    assert state.kind is ReleasePublicationWorkStateKind.TERMINAL
    assert state.terminal_result is ReleasePublicationWorkResultKind.PUBLISHED


def test_current_outcome_inspects_once_and_commits_absence(unknown):
    inspector = CountingInspector()
    result = _current(unknown, inspector).finalize_current_outcome(
        EXECUTION, ATTEMPT
    )
    assert inspector.count == 1
    assert result.kind.value == "absence_confirmed"
    state = DatabaseReleasePublicationWorkStateLookup(
        unknown[0]
    ).get_work_state(_bound_request(unknown))
    assert state.kind is (
        ReleasePublicationWorkStateKind.ATTEMPT_ONE_ABSENCE_RECOVERED
    )


def test_exact_finalizer_retry_does_not_inspect_again(unknown):
    first_inspector = CountingInspector(observed(unknown))
    first = _current(unknown, first_inspector).finalize_current_outcome(
        EXECUTION, ATTEMPT
    )
    retry_inspector = CountingInspector()
    retry = _current(unknown, retry_inspector).finalize_current_outcome(
        EXECUTION, ATTEMPT
    )
    assert retry == first
    assert retry_inspector.count == 0
