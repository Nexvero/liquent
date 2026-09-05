import pytest
from sqlalchemy import text

from liquent_platform.identity.release_publication import (
    ReleasePublicationAttemptId,
    ReleasePublicationReconciliationKind,
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationReconciliationUnavailable,
)
from liquent_platform.persistence.release_publication_reconciliation import (
    DatabaseReleasePublicationUnknownOutcomeReconciliation,
)
from liquent_platform.persistence.release_publication_retry_create import (
    DatabaseReleasePublicationRetryImmutableCreate,
)
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, checker, ready
from test_release_publication_reconciliation import unknown
from test_release_publication_retry import recovered_absence
from test_release_publication_retry_create import (
    ATTEMPT_TWO,
    Creator,
    prepared_retry,
)
from test_release_publication_target import Inspector


@pytest.fixture
def retry_unknown(prepared_retry):
    DatabaseReleasePublicationRetryImmutableCreate(
        prepared_retry[0], artifact_integrity=checker(prepared_retry),
        target_inspector=Inspector(), immutable_creator=Creator(prepared_retry[0]),
    ).create_retry_publication(EXECUTION, ATTEMPT_TWO)
    return prepared_retry


def service(retry_unknown, inspector):
    return DatabaseReleasePublicationUnknownOutcomeReconciliation(
        retry_unknown[0], target_inspector=inspector,
    )


def observed(retry_unknown, **changes):
    with retry_unknown[0].connect() as connection:
        wheel = connection.scalar(text(
            "SELECT wheel_sha256 FROM release_publication_handoffs"
        ))
    values = dict(
        canonical_artifact_id="artifact-263",
        provider_revision="provider-revision-263",
        package_name="liquent", package_version="1.2.3",
        wheel_sha256=wheel, visible=True,
    )
    values.update(changes)
    return ReleasePublicationTargetObservation(**values)


def test_attempt_two_exact_visible_effect_is_published_confirmed_read_only(
    retry_unknown,
):
    result = service(
        retry_unknown, Inspector(observed(retry_unknown))
    ).reconcile_unknown_outcome(EXECUTION, ATTEMPT_TWO)
    assert result.kind is ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED
    assert result.current_authority is True
    assert result.attempt_id == ATTEMPT_TWO
    with retry_unknown[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status"
            " FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
            " WHERE attempt.attempt_number=2"
        )).one() == ("outcome_unknown", "outcome_unknown")
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_receipts"
        )) == 0


def test_attempt_two_confirmed_absence_does_not_create_again(retry_unknown):
    inspector = Inspector()
    result = service(retry_unknown, inspector).reconcile_unknown_outcome(
        EXECUTION, ATTEMPT_TWO
    )
    assert result.kind is ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED
    assert result.observation is None
    assert len(inspector.calls) == 1


@pytest.mark.parametrize("changes", [
    {"wheel_sha256": "0" * 64},
    {"package_name": "other"},
    {"package_version": "9.9.9"},
    {"visible": False},
])
def test_attempt_two_different_or_invisible_effect_is_conflict(
    retry_unknown, changes,
):
    result = service(
        retry_unknown, Inspector(observed(retry_unknown, **changes))
    ).reconcile_unknown_outcome(EXECUTION, ATTEMPT_TWO)
    assert result.kind is ReleasePublicationReconciliationKind.CONFLICT


def test_attempt_two_revocation_still_inspects_external_reality(retry_unknown):
    with retry_unknown[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_registry_revision_keys SET status='revoked'"
        ))
    inspector = Inspector(observed(retry_unknown))
    result = service(retry_unknown, inspector).reconcile_unknown_outcome(
        EXECUTION, ATTEMPT_TWO
    )
    assert result.kind is ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED
    assert result.current_authority is False
    assert len(inspector.calls) == 1


def test_prepared_attempt_two_never_reaches_reconciliation_provider(prepared_retry):
    class Broken:
        def inspect_target(self, target): raise AssertionError("must not inspect")
    assert DatabaseReleasePublicationUnknownOutcomeReconciliation(
        prepared_retry[0], target_inspector=Broken()
    ).reconcile_unknown_outcome(EXECUTION, ATTEMPT_TWO) is None


def test_attempt_two_provider_unknown_is_detail_free_and_persisted(retry_unknown):
    class Broken:
        def inspect_target(self, target): raise TimeoutError("provider detail")
    with pytest.raises(ReleasePublicationReconciliationUnavailable) as raised:
        service(retry_unknown, Broken()).reconcile_unknown_outcome(
            EXECUTION, ATTEMPT_TWO
        )
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    with retry_unknown[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM release_publication_execution_attempts"
            " WHERE attempt_number=2"
        )) == "outcome_unknown"


def test_unknown_retry_attempt_is_neutral_without_provider_access(retry_unknown):
    inspector = Inspector()
    assert service(retry_unknown, inspector).reconcile_unknown_outcome(
        EXECUTION, ReleasePublicationAttemptId("unknown-263")
    ) is None
    assert inspector.calls == []
