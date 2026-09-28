from datetime import datetime, timezone

from sqlalchemy import text

from liquent_platform.identity.release_publication import (
    ReleasePublicationAttemptId,
    ReleasePublicationCreateAcknowledgement,
    ReleasePublicationFinalStatus,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationReconciliationKind,
    ReleasePublicationRecoveryId,
)
from liquent_platform.persistence.release_publication_create import (
    DatabaseReleasePublicationImmutableCreate,
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
from liquent_platform.persistence.release_publication_retry import (
    DatabaseReleasePublicationRetryAttemptPreflight,
)
from liquent_platform.persistence.release_publication_retry_create import (
    DatabaseReleasePublicationRetryImmutableCreate,
)
from liquent_platform.persistence.release_publication_target import (
    DatabaseReleasePublicationTargetInspection,
)
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, checker, ready
from test_release_publication_reconciliation import observed
from test_release_publication_target import Inspector


ATTEMPT_TWO = ReleasePublicationAttemptId("attempt-lq265-two")
NOW = datetime(2026, 8, 19, 8, tzinfo=timezone.utc)


class AuditCreator:
    def __init__(self, engine):
        self.engine = engine
        self.keys = []

    def create_immutable(self, target, artifacts, idempotency_key):
        with self.engine.connect() as connection:
            assert connection.scalar(text(
                "SELECT count(*) FROM release_publication_execution_attempts"
                " WHERE status='write_started'"
            )) == 1
        self.keys.append(idempotency_key)
        return ReleasePublicationCreateAcknowledgement(
            f"request-lq265-{len(self.keys)}"
        )


def _reconciliation(engine, inspector):
    return DatabaseReleasePublicationUnknownOutcomeReconciliation(
        engine, target_inspector=inspector,
    )


def _first_attempt_absence_then_prepare_second(ready, creator):
    integrity = checker(ready)
    first = DatabaseReleasePublicationImmutableCreate(
        ready[0],
        target_inspection=DatabaseReleasePublicationTargetInspection(
            ready[0], artifact_integrity=integrity, target_inspector=Inspector(),
        ),
        immutable_creator=creator,
    ).create_publication(EXECUTION, ATTEMPT)
    assert first.acknowledgement.provider_request_id == "request-lq265-1"
    recovered = DatabaseReleasePublicationRecoveryFinalizer(
        ready[0], reconciliation=_reconciliation(ready[0], Inspector()),
        generate_recovery_id=lambda: ReleasePublicationRecoveryId(
            "recovery-lq265-one"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "unused-lq265-one"
        ),
        clock=lambda: NOW,
    ).finalize_recovery(EXECUTION, ATTEMPT)
    assert recovered.retry_eligible is True
    prepared = DatabaseReleasePublicationRetryAttemptPreflight(
        ready[0], artifact_integrity=integrity, target_inspector=Inspector(),
        generate_attempt_id=lambda: ATTEMPT_TWO, clock=lambda: NOW,
    ).prepare_retry_attempt(EXECUTION, ATTEMPT)
    assert prepared.attempt_id == ATTEMPT_TWO
    return integrity


def _write_second_unknown(ready, creator, integrity):
    result = DatabaseReleasePublicationRetryImmutableCreate(
        ready[0], artifact_integrity=integrity,
        target_inspector=Inspector(), immutable_creator=creator,
    ).create_retry_publication(EXECUTION, ATTEMPT_TWO)
    assert result.acknowledgement.provider_request_id == "request-lq265-2"


def test_two_attempt_lifecycle_reaches_published_with_exactly_two_creates(ready):
    creator = AuditCreator(ready[0])
    integrity = _first_attempt_absence_then_prepare_second(ready, creator)
    _write_second_unknown(ready, creator, integrity)
    observation = observed(ready)
    result = DatabaseReleasePublicationReconciliationFinalizer(
        ready[0], reconciliation=_reconciliation(
            ready[0], Inspector(observation)
        ),
        generate_receipt_id=lambda: ReleasePublicationProviderReceiptId(
            "receipt-lq265"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "unused-lq265-published"
        ),
        clock=lambda: NOW,
    ).finalize_reconciliation(EXECUTION, ATTEMPT_TWO)
    assert result.status is ReleasePublicationFinalStatus.PUBLISHED
    assert creator.keys == [EXECUTION, ATTEMPT_TWO]
    with ready[0].connect() as connection:
        assert connection.execute(text(
            "SELECT attempt_number,status FROM release_publication_execution_attempts"
            " ORDER BY attempt_number"
        )).all() == [(1, "reconciled"), (2, "reconciled")]
        assert connection.scalar(text(
            "SELECT status FROM release_publication_executions"
        )) == "published"
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_receipts"
        )) == 1


def test_second_absence_is_terminal_and_cannot_prepare_attempt_three(ready):
    creator = AuditCreator(ready[0])
    integrity = _first_attempt_absence_then_prepare_second(ready, creator)
    _write_second_unknown(ready, creator, integrity)
    result = DatabaseReleasePublicationRecoveryFinalizer(
        ready[0], reconciliation=_reconciliation(ready[0], Inspector()),
        generate_recovery_id=lambda: ReleasePublicationRecoveryId(
            "recovery-lq265-two"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "unused-lq265-two"
        ),
        clock=lambda: NOW,
    ).finalize_recovery(EXECUTION, ATTEMPT_TWO)
    assert result.kind is ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED
    assert result.retry_eligible is False
    inspector = Inspector()
    assert DatabaseReleasePublicationRetryAttemptPreflight(
        ready[0], artifact_integrity=integrity, target_inspector=inspector,
        generate_attempt_id=lambda: ReleasePublicationAttemptId(
            "must-not-be-attempt-three"
        ),
    ).prepare_retry_attempt(EXECUTION, ATTEMPT_TWO) is None
    assert inspector.calls == []
    with ready[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_execution_attempts"
        )) == 2
        assert connection.scalar(text(
            "SELECT status FROM release_publication_executions"
        )) == "not_published"


def test_second_conflict_is_terminal_without_receipt_or_third_create(ready):
    creator = AuditCreator(ready[0])
    integrity = _first_attempt_absence_then_prepare_second(ready, creator)
    _write_second_unknown(ready, creator, integrity)
    conflict = observed(ready, wheel_sha256="0" * 64)
    result = DatabaseReleasePublicationRecoveryFinalizer(
        ready[0], reconciliation=_reconciliation(
            ready[0], Inspector(conflict)
        ),
        generate_recovery_id=lambda: ReleasePublicationRecoveryId(
            "recovery-lq265-conflict"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "reassessment-lq265-conflict"
        ),
        clock=lambda: NOW,
    ).finalize_recovery(EXECUTION, ATTEMPT_TWO)
    assert result.kind is ReleasePublicationReconciliationKind.CONFLICT
    assert result.retry_eligible is False
    assert len(creator.keys) == 2
    with ready[0].connect() as connection:
        assert connection.execute(text(
            "SELECT (SELECT status FROM release_publication_executions),"
            " (SELECT count(*) FROM release_publication_receipts),"
            " (SELECT count(*) FROM release_publication_reassessments),"
            " (SELECT count(*) FROM release_publication_execution_attempts)"
        )).one() == ("publication_conflict", 0, 1, 2)


def test_revocation_after_first_recovery_blocks_second_attempt_before_provider(ready):
    creator = AuditCreator(ready[0])
    integrity = _first_attempt_absence_then_prepare_second(ready, creator)
    with ready[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_registry_revision_keys SET status='revoked'"
        ))
    inspector = Inspector()
    assert DatabaseReleasePublicationRetryImmutableCreate(
        ready[0], artifact_integrity=integrity,
        target_inspector=inspector, immutable_creator=creator,
    ).create_retry_publication(EXECUTION, ATTEMPT_TWO) is None
    assert inspector.calls == []
    assert creator.keys == [EXECUTION]
