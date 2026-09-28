from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from liquent_platform.identity.release_publication import (
    ReleasePublicationReassessmentId,
    ReleasePublicationReconciliationKind,
    ReleasePublicationRecoveryId,
)
from liquent_platform.persistence.release_publication_reconciliation import DatabaseReleasePublicationUnknownOutcomeReconciliation
from liquent_platform.persistence.release_publication_recovery import DatabaseReleasePublicationRecoveryFinalizer
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, ready
from test_release_publication_reconciliation import observed, unknown
from test_release_publication_target import Inspector


RECOVERY = ReleasePublicationRecoveryId("recovery-260")
REASSESSMENT = ReleasePublicationReassessmentId("reassessment-260")
NOW = datetime(2026, 8, 18, 23, tzinfo=timezone.utc)


def reconciliation(unknown, inspector):
    return DatabaseReleasePublicationUnknownOutcomeReconciliation(
        unknown[0], target_inspector=inspector,
    )


def finalizer(unknown, reconcile, recovery=lambda: RECOVERY, reassessment=lambda: REASSESSMENT):
    return DatabaseReleasePublicationRecoveryFinalizer(
        unknown[0], reconciliation=reconcile,
        generate_recovery_id=recovery, generate_reassessment_id=reassessment,
        clock=lambda: NOW,
    )


def test_confirmed_absence_closes_attempt_without_creating_attempt_two(unknown):
    result = finalizer(
        unknown, reconciliation(unknown, Inspector())
    ).finalize_recovery(EXECUTION, ATTEMPT)
    assert result.kind is ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED
    assert result.retry_eligible is True
    assert result.reassessment_id is None
    with unknown[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status,attempt.finished_at IS NOT NULL "
            "FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("prepared", "reconciled", 1)
        assert connection.execute(text(
            "SELECT kind,current_authority FROM release_publication_recovery_decisions"
        )).one() == ("absence_confirmed", 1)
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_execution_attempts"
        )) == 1


def test_absence_after_revocation_is_closed_but_not_retry_eligible(unknown):
    with unknown[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_registry_revision_keys SET status='revoked'"
        ))
    result = finalizer(
        unknown, reconciliation(unknown, Inspector())
    ).finalize_recovery(EXECUTION, ATTEMPT)
    assert result.retry_eligible is False
    with unknown[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_reassessments"
        )) == 0


def test_conflict_closes_attempt_and_atomically_opens_reassessment(unknown):
    conflict = observed(unknown, wheel_sha256="0" * 64)
    result = finalizer(
        unknown, reconciliation(unknown, Inspector(conflict))
    ).finalize_recovery(EXECUTION, ATTEMPT)
    assert result.kind is ReleasePublicationReconciliationKind.CONFLICT
    assert result.retry_eligible is False
    assert result.reassessment_id == REASSESSMENT
    with unknown[0].connect() as connection:
        assert connection.execute(text(
            "SELECT kind,external_artifact_id,provider_revision,reassessment_id "
            "FROM release_publication_recovery_decisions"
        )).one() == (
            "conflict", b"artifact-258", b"provider-revision-258",
            REASSESSMENT.value.encode(),
        )
        assert connection.execute(text(
            "SELECT execution.status,attempt.status FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("outcome_unknown", "reconciled")
        assert connection.execute(text(
            "SELECT intent,status FROM release_publication_reassessments"
        )).one() == ("reassess", "pending")


def test_exact_retry_returns_same_recovery_without_provider_or_ids(unknown):
    first = finalizer(
        unknown, reconciliation(unknown, Inspector())
    ).finalize_recovery(EXECUTION, ATTEMPT)
    class Broken:
        def reconcile_unknown_outcome(self, execution_id, attempt_id):
            raise AssertionError("must not inspect")
    def broken(): raise AssertionError("must not generate")
    retry = finalizer(unknown, Broken(), broken, broken).finalize_recovery(
        EXECUTION, ATTEMPT
    )
    assert retry == first


def test_published_confirmation_is_left_for_receipt_finalizer(unknown):
    def broken(): raise AssertionError("must not generate")
    result = finalizer(
        unknown, reconciliation(unknown, Inspector(observed(unknown))),
        broken, broken,
    ).finalize_recovery(EXECUTION, ATTEMPT)
    assert result is None
    with unknown[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_recovery_decisions"
        )) == 0


def test_conflict_never_creates_receipt_or_attempt_two(unknown):
    finalizer(
        unknown, reconciliation(unknown, Inspector(observed(
            unknown, package_version="9.9.9"
        )))
    ).finalize_recovery(EXECUTION, ATTEMPT)
    with unknown[0].connect() as connection:
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM release_publication_receipts),"
            "(SELECT count(*) FROM release_publication_execution_attempts)"
        )).one() == (0, 1)
