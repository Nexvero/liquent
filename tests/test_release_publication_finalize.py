from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from liquent_platform.identity.release_publication import (
    ReleasePublicationFinalStatus,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
)
from liquent_platform.persistence.release_publication_finalize import (
    DatabaseReleasePublicationReconciliationFinalizer,
)
from liquent_platform.persistence.release_publication_reconciliation import (
    DatabaseReleasePublicationUnknownOutcomeReconciliation,
)
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, ready
from test_release_publication_reconciliation import observed, unknown
from test_release_publication_target import Inspector


RECEIPT = ReleasePublicationProviderReceiptId("receipt-259")
REASSESSMENT = ReleasePublicationReassessmentId("reassessment-259")
NOW = datetime(2026, 8, 18, 21, tzinfo=timezone.utc)


def reconciliation(unknown, inspector):
    return DatabaseReleasePublicationUnknownOutcomeReconciliation(
        unknown[0], target_inspector=inspector,
    )


def finalizer(unknown, reconcile, receipt=lambda: RECEIPT, reassessment=lambda: REASSESSMENT):
    return DatabaseReleasePublicationReconciliationFinalizer(
        unknown[0], reconciliation=reconcile,
        generate_receipt_id=receipt, generate_reassessment_id=reassessment,
        clock=lambda: NOW,
    )


def test_atomically_persists_current_authority_receipt_and_closes_attempt(unknown):
    subject = finalizer(unknown, reconciliation(unknown, Inspector(observed(unknown))))
    result = subject.finalize_reconciliation(EXECUTION, ATTEMPT)
    assert result.status is ReleasePublicationFinalStatus.PUBLISHED
    assert result.receipt_id == RECEIPT
    assert result.reassessment_id is None
    with unknown[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status,attempt.finished_at IS NOT NULL "
            "FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("published", "reconciled", 1)
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM release_publication_receipts),"
            "(SELECT count(*) FROM release_publication_receipt_reconciliations),"
            "(SELECT count(*) FROM release_publication_reassessments)"
        )).one() == (1, 1, 0)


def test_exact_retry_returns_receipt_without_provider_or_new_ids(unknown):
    first = finalizer(
        unknown, reconciliation(unknown, Inspector(observed(unknown)))
    ).finalize_reconciliation(EXECUTION, ATTEMPT)
    class Broken:
        def reconcile_unknown_outcome(self, execution_id, attempt_id):
            raise AssertionError("must not inspect")
    def broken(): raise AssertionError("must not generate")
    retry = finalizer(unknown, Broken(), broken, broken).finalize_reconciliation(
        EXECUTION, ATTEMPT
    )
    assert retry == first


def test_revoked_authority_atomically_preserves_receipt_and_pending_reassessment(unknown):
    with unknown[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_registry_revision_keys SET status='revoked'"
        ))
    result = finalizer(
        unknown, reconciliation(unknown, Inspector(observed(unknown)))
    ).finalize_reconciliation(EXECUTION, ATTEMPT)
    assert result.status is ReleasePublicationFinalStatus.PUBLISHED_REASSESSMENT_REQUIRED
    assert result.reassessment_id == REASSESSMENT
    with unknown[0].connect() as connection:
        assert connection.execute(text(
            "SELECT intent,status FROM release_publication_reassessments"
        )).one() == ("reassess", "pending")
        assert connection.execute(text(
            "SELECT status FROM release_publication_receipt_reconciliations"
        )).scalar_one() == "published_reassessment_required"
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_execution_reassessments"
        )) == 1


def test_revocation_after_read_only_reconciliation_is_caught_at_commit(unknown):
    base = reconciliation(unknown, Inspector(observed(unknown)))
    class Revoking:
        def reconcile_unknown_outcome(self, execution_id, attempt_id):
            outcome = base.reconcile_unknown_outcome(execution_id, attempt_id)
            assert outcome.current_authority is True
            with unknown[0].begin() as connection:
                connection.execute(text(
                    "UPDATE release_publication_revision_publishers SET status='inactive'"
                ))
            return outcome
    result = finalizer(unknown, Revoking()).finalize_reconciliation(EXECUTION, ATTEMPT)
    assert result.status is ReleasePublicationFinalStatus.PUBLISHED_REASSESSMENT_REQUIRED


@pytest.mark.parametrize("inspector", [
    Inspector(),
    Inspector("conflict-placeholder"),
])
def test_absence_or_conflict_does_not_finalize_or_generate_ids(unknown, inspector):
    if inspector.result == "conflict-placeholder":
        inspector.result = observed(unknown, wheel_sha256="0" * 64)
    def broken(): raise AssertionError("must not generate")
    result = finalizer(
        unknown, reconciliation(unknown, inspector), broken, broken
    ).finalize_reconciliation(EXECUTION, ATTEMPT)
    assert result is None
    with unknown[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("outcome_unknown", "outcome_unknown")
        assert connection.scalar(text("SELECT count(*) FROM release_publication_receipts")) == 0
