from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from liquent_platform.identity.release_publication import (
    PreparedReleasePublicationAttempt,
    ReleasePublicationAttemptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.identity_errors import ReleasePublicationRetryAttemptUnavailable
from liquent_platform.persistence.release_publication_reconciliation import DatabaseReleasePublicationUnknownOutcomeReconciliation
from liquent_platform.persistence.release_publication_recovery import DatabaseReleasePublicationRecoveryFinalizer
from liquent_platform.persistence.release_publication_retry import DatabaseReleasePublicationRetryAttemptPreflight
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, checker, ready
from test_release_publication_reconciliation import unknown
from test_release_publication_target import Inspector


ATTEMPT_TWO = ReleasePublicationAttemptId("attempt-261")
NOW = datetime(2026, 8, 19, 1, tzinfo=timezone.utc)


@pytest.fixture
def recovered_absence(unknown):
    reconciliation = DatabaseReleasePublicationUnknownOutcomeReconciliation(
        unknown[0], target_inspector=Inspector(),
    )
    result = DatabaseReleasePublicationRecoveryFinalizer(
        unknown[0], reconciliation=reconciliation,
        generate_recovery_id=lambda: ReleasePublicationRecoveryId("recovery-261"),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId("unused-261"),
        clock=lambda: NOW,
    ).finalize_recovery(EXECUTION, ATTEMPT)
    assert result.retry_eligible is True
    return unknown


def preflight(recovered_absence, inspector, generate=lambda: ATTEMPT_TWO):
    return DatabaseReleasePublicationRetryAttemptPreflight(
        recovered_absence[0], artifact_integrity=checker(recovered_absence),
        target_inspector=inspector, generate_attempt_id=generate,
        clock=lambda: NOW,
    )


def test_fresh_integrity_authority_and_absence_prepare_attempt_two(recovered_absence):
    inspector = Inspector()
    result = preflight(recovered_absence, inspector).prepare_retry_attempt(
        EXECUTION, ATTEMPT
    )
    assert result == PreparedReleasePublicationAttempt(
        EXECUTION, ATTEMPT_TWO, result.handoff_id, 2
    )
    assert len(inspector.calls) == 1
    with recovered_absence[0].connect() as connection:
        rows = connection.execute(text(
            "SELECT attempt_number,status,finished_at FROM "
            "release_publication_execution_attempts ORDER BY attempt_number"
        )).all()
        assert rows[0][0:2] == (1, "reconciled") and rows[0][2] is not None
        assert rows[1] == (2, "prepared", None)
        assert connection.scalar(text("SELECT count(*) FROM release_publication_receipts")) == 0


def test_exact_retry_returns_attempt_two_without_integrity_provider_or_id(recovered_absence):
    first = preflight(recovered_absence, Inspector()).prepare_retry_attempt(EXECUTION, ATTEMPT)
    class BrokenIntegrity:
        def verify_artifacts(self, execution_id, attempt_id):
            raise AssertionError("must not verify")
    class BrokenInspector:
        def inspect_target(self, target): raise AssertionError("must not inspect")
    def broken(): raise AssertionError("must not generate")
    subject = DatabaseReleasePublicationRetryAttemptPreflight(
        recovered_absence[0], artifact_integrity=BrokenIntegrity(),
        target_inspector=BrokenInspector(), generate_attempt_id=broken,
    )
    assert subject.prepare_retry_attempt(EXECUTION, ATTEMPT) == first


def test_revocation_after_recovery_blocks_attempt_two_before_target_read(recovered_absence):
    with recovered_absence[0].begin() as connection:
        connection.execute(text("UPDATE release_registry_revision_keys SET status='revoked'"))
    inspector = Inspector()
    assert preflight(recovered_absence, inspector).prepare_retry_attempt(
        EXECUTION, ATTEMPT
    ) is None
    assert inspector.calls == []


def test_target_no_longer_absent_blocks_attempt_two(recovered_absence):
    with recovered_absence[0].connect() as connection:
        wheel = connection.scalar(text("SELECT wheel_sha256 FROM release_publication_handoffs"))
    inspector = Inspector(ReleasePublicationTargetObservation(
        "artifact-261", "revision-261", "liquent", "1.2.3", wheel, True,
    ))
    assert preflight(recovered_absence, inspector).prepare_retry_attempt(
        EXECUTION, ATTEMPT
    ) is None
    with recovered_absence[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_execution_attempts"
        )) == 1


def test_non_absence_recovery_is_not_retry_eligible(unknown):
    with unknown[0].connect() as connection:
        wheel = connection.scalar(text("SELECT wheel_sha256 FROM release_publication_handoffs"))
    conflict = ReleasePublicationTargetObservation(
        "artifact-conflict-261", "revision-conflict-261", "liquent", "1.2.3",
        "0" * 64, True,
    )
    DatabaseReleasePublicationRecoveryFinalizer(
        unknown[0], reconciliation=DatabaseReleasePublicationUnknownOutcomeReconciliation(
            unknown[0], target_inspector=Inspector(conflict),
        ), generate_recovery_id=lambda: ReleasePublicationRecoveryId("conflict-261"),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId("reassessment-261"),
        clock=lambda: NOW,
    ).finalize_recovery(EXECUTION, ATTEMPT)
    inspector = Inspector()
    assert preflight(unknown, inspector).prepare_retry_attempt(EXECUTION, ATTEMPT) is None
    assert inspector.calls == []


def test_provider_read_failure_is_detail_free_and_creates_no_attempt(recovered_absence):
    class Broken:
        def inspect_target(self, target): raise TimeoutError("provider detail")
    with pytest.raises(ReleasePublicationRetryAttemptUnavailable) as raised:
        preflight(recovered_absence, Broken()).prepare_retry_attempt(EXECUTION, ATTEMPT)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    with recovered_absence[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_execution_attempts"
        )) == 1
