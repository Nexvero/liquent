from datetime import datetime, timezone

from sqlalchemy import text

from liquent_platform.identity.release_publication import (
    ReleasePublicationFinalStatus,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationReconciliationKind,
    ReleasePublicationRecoveryId,
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
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, ready
from test_release_publication_reconciliation import unknown
from test_release_publication_retry import recovered_absence
from test_release_publication_retry_create import prepared_retry
from test_release_publication_retry_reconciliation import (
    ATTEMPT_TWO,
    observed,
    retry_unknown,
)
from test_release_publication_target import Inspector


NOW = datetime(2026, 8, 19, 6, tzinfo=timezone.utc)
RECEIPT = ReleasePublicationProviderReceiptId("receipt-264")
RECOVERY = ReleasePublicationRecoveryId("recovery-264")
REASSESSMENT = ReleasePublicationReassessmentId("reassessment-264")


def reconciliation(retry_unknown, inspector):
    return DatabaseReleasePublicationUnknownOutcomeReconciliation(
        retry_unknown[0], target_inspector=inspector,
    )


def published_finalizer(retry_unknown, reconcile):
    return DatabaseReleasePublicationReconciliationFinalizer(
        retry_unknown[0], reconciliation=reconcile,
        generate_receipt_id=lambda: RECEIPT,
        generate_reassessment_id=lambda: REASSESSMENT,
        clock=lambda: NOW,
    )


def recovery_finalizer(retry_unknown, reconcile):
    return DatabaseReleasePublicationRecoveryFinalizer(
        retry_unknown[0], reconciliation=reconcile,
        generate_recovery_id=lambda: RECOVERY,
        generate_reassessment_id=lambda: REASSESSMENT,
        clock=lambda: NOW,
    )


def test_attempt_two_published_is_atomically_finalized_as_receipt(retry_unknown):
    result = published_finalizer(
        retry_unknown,
        reconciliation(retry_unknown, Inspector(observed(retry_unknown))),
    ).finalize_reconciliation(EXECUTION, ATTEMPT_TWO)
    assert result.status is ReleasePublicationFinalStatus.PUBLISHED
    assert result.attempt_id == ATTEMPT_TWO
    with retry_unknown[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status,attempt.finished_at IS NOT NULL"
            " FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
            " WHERE attempt.attempt_number=2"
        )).one() == ("published", "reconciled", 1)
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_receipts"
        )) == 1


def test_attempt_two_published_after_revocation_requires_reassessment(retry_unknown):
    with retry_unknown[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_registry_revision_keys SET status='revoked'"
        ))
    result = published_finalizer(
        retry_unknown,
        reconciliation(retry_unknown, Inspector(observed(retry_unknown))),
    ).finalize_reconciliation(EXECUTION, ATTEMPT_TWO)
    assert result.status is ReleasePublicationFinalStatus.PUBLISHED_REASSESSMENT_REQUIRED
    assert result.reassessment_id == REASSESSMENT


def test_attempt_two_absence_is_terminal_without_attempt_three(retry_unknown):
    result = recovery_finalizer(
        retry_unknown, reconciliation(retry_unknown, Inspector())
    ).finalize_recovery(EXECUTION, ATTEMPT_TWO)
    assert result.kind is ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED
    assert result.retry_eligible is False
    with retry_unknown[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM release_publication_executions"
        )) == "not_published"
        assert connection.execute(text(
            "SELECT attempt_number,status FROM release_publication_execution_attempts"
            " ORDER BY attempt_number"
        )).all() == [(1, "reconciled"), (2, "reconciled")]
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_execution_attempts"
        )) == 2


def test_attempt_two_conflict_is_terminal_with_reassessment(retry_unknown):
    conflict = observed(retry_unknown, wheel_sha256="0" * 64)
    result = recovery_finalizer(
        retry_unknown, reconciliation(retry_unknown, Inspector(conflict))
    ).finalize_recovery(EXECUTION, ATTEMPT_TWO)
    assert result.kind is ReleasePublicationReconciliationKind.CONFLICT
    assert result.retry_eligible is False
    assert result.reassessment_id == REASSESSMENT
    with retry_unknown[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM release_publication_executions"
        )) == "publication_conflict"
        assert connection.execute(text(
            "SELECT intent,status FROM release_publication_reassessments"
        )).one() == ("reassess", "pending")


def test_exact_attempt_two_terminal_retry_avoids_provider_and_ids(retry_unknown):
    first = recovery_finalizer(
        retry_unknown, reconciliation(retry_unknown, Inspector())
    ).finalize_recovery(EXECUTION, ATTEMPT_TWO)
    class Broken:
        def reconcile_unknown_outcome(self, execution_id, attempt_id):
            raise AssertionError("must not inspect")
    def broken(): raise AssertionError("must not generate")
    retry = DatabaseReleasePublicationRecoveryFinalizer(
        retry_unknown[0], reconciliation=Broken(),
        generate_recovery_id=broken, generate_reassessment_id=broken,
    ).finalize_recovery(EXECUTION, ATTEMPT_TWO)
    assert retry == first
