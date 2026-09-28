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
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, ready
from test_release_publication_target import Inspector


@pytest.fixture
def unknown(ready):
    with ready[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_publication_executions SET status='outcome_unknown'"
        ))
        connection.execute(text(
            "UPDATE release_publication_execution_attempts SET status='outcome_unknown'"
        ))
    return ready


def service(unknown, inspector):
    return DatabaseReleasePublicationUnknownOutcomeReconciliation(
        unknown[0], target_inspector=inspector,
    )


def observed(unknown, **changes):
    with unknown[0].connect() as connection:
        wheel = connection.scalar(text(
            "SELECT wheel_sha256 FROM release_publication_handoffs"
        ))
    values = dict(
        canonical_artifact_id="artifact-258",
        provider_revision="provider-revision-258",
        package_name="liquent", package_version="1.2.3",
        wheel_sha256=wheel, visible=True,
    )
    values.update(changes)
    return ReleasePublicationTargetObservation(**values)


def test_exact_visible_effect_is_published_confirmed_read_only(unknown):
    inspector = Inspector(observed(unknown))
    result = service(unknown, inspector).reconcile_unknown_outcome(EXECUTION, ATTEMPT)
    assert result.kind is ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED
    assert result.current_authority is True
    assert result.observation.provider_revision == "provider-revision-258"
    with unknown[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("outcome_unknown", "outcome_unknown")
        assert connection.scalar(text("SELECT count(*) FROM release_publication_receipts")) == 0


def test_confirmed_absence_is_explicit_but_does_not_retry(unknown):
    inspector = Inspector()
    result = service(unknown, inspector).reconcile_unknown_outcome(EXECUTION, ATTEMPT)
    assert result.kind is ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED
    assert result.observation is None
    assert len(inspector.calls) == 1


@pytest.mark.parametrize("changes", [
    {"wheel_sha256": "0" * 64},
    {"package_name": "other"},
    {"package_version": "9.9.9"},
    {"visible": False},
])
def test_different_or_invisible_effect_is_conflict(unknown, changes):
    result = service(unknown, Inspector(observed(unknown, **changes))).reconcile_unknown_outcome(
        EXECUTION, ATTEMPT
    )
    assert result.kind is ReleasePublicationReconciliationKind.CONFLICT


def test_revoked_authority_still_inspects_external_reality(unknown):
    with unknown[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_registry_revision_keys SET status='revoked'"
        ))
    inspector = Inspector(observed(unknown))
    result = service(unknown, inspector).reconcile_unknown_outcome(EXECUTION, ATTEMPT)
    assert result.kind is ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED
    assert result.current_authority is False
    assert len(inspector.calls) == 1


def test_non_unknown_attempt_never_reaches_provider(ready):
    class Broken:
        def inspect_target(self, target): raise AssertionError("must not inspect")
    assert DatabaseReleasePublicationUnknownOutcomeReconciliation(
        ready[0], target_inspector=Broken()
    ).reconcile_unknown_outcome(EXECUTION, ATTEMPT) is None


def test_technical_provider_unknown_remains_detail_free_and_persisted_unknown(unknown):
    class Broken:
        def inspect_target(self, target): raise TimeoutError("provider detail")
    with pytest.raises(ReleasePublicationReconciliationUnavailable) as raised:
        service(unknown, Broken()).reconcile_unknown_outcome(EXECUTION, ATTEMPT)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    with unknown[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM release_publication_execution_attempts"
        )) == "outcome_unknown"


def test_unknown_attempt_is_neutral_without_provider_access(unknown):
    inspector = Inspector()
    assert service(unknown, inspector).reconcile_unknown_outcome(
        EXECUTION, ReleasePublicationAttemptId("unknown")
    ) is None
    assert inspector.calls == []
