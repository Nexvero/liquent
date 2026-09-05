import pytest
from sqlalchemy import text

from liquent_platform.identity.release_publication import (
    ReleasePublicationCreateAcknowledgement,
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationRetryCreateUnavailable,
)
from liquent_platform.persistence.release_publication_retry_create import (
    DatabaseReleasePublicationRetryImmutableCreate,
)
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, checker, ready
from test_release_publication_retry import ATTEMPT_TWO, preflight, recovered_absence
from test_release_publication_reconciliation import unknown
from test_release_publication_target import Inspector


class Creator:
    def __init__(self, engine, result=None, error=None):
        self.engine = engine
        self.result = result or ReleasePublicationCreateAcknowledgement("request-262")
        self.error = error
        self.calls = []

    def create_immutable(self, target, artifacts, idempotency_key):
        with self.engine.connect() as connection:
            state = connection.execute(text(
                "SELECT execution.status,attempt.status"
                " FROM release_publication_executions execution"
                " JOIN release_publication_execution_attempts attempt"
                " ON attempt.execution_id=execution.execution_id"
                " WHERE attempt.attempt_number=2"
            )).one()
        assert state == ("prepared", "write_started")
        self.calls.append((target, artifacts, idempotency_key))
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def prepared_retry(recovered_absence):
    result = preflight(recovered_absence, Inspector()).prepare_retry_attempt(
        EXECUTION, ATTEMPT
    )
    assert result.attempt_id == ATTEMPT_TWO
    return recovered_absence


def service(prepared_retry, creator, inspector=None, integrity=None):
    return DatabaseReleasePublicationRetryImmutableCreate(
        prepared_retry[0],
        artifact_integrity=integrity or checker(prepared_retry),
        target_inspector=inspector or Inspector(),
        immutable_creator=creator,
    )


def test_attempt_two_commits_write_start_then_preserves_unknown(prepared_retry):
    creator = Creator(prepared_retry[0])
    result = service(prepared_retry, creator).create_retry_publication(
        EXECUTION, ATTEMPT_TWO
    )
    assert result.acknowledgement.provider_request_id == "request-262"
    assert creator.calls[0][2] == ATTEMPT_TWO
    with prepared_retry[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status,attempt.finished_at"
            " FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
            " WHERE attempt.attempt_number=2"
        )).one() == ("outcome_unknown", "outcome_unknown", None)
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_receipts"
        )) == 0


def test_retry_after_possible_effect_never_reads_or_creates_again(prepared_retry):
    first = service(prepared_retry, Creator(prepared_retry[0])).create_retry_publication(
        EXECUTION, ATTEMPT_TWO
    )
    class BrokenIntegrity:
        def verify_artifacts(self, execution_id, attempt_id):
            raise AssertionError("must not verify")
    class BrokenInspector:
        def inspect_target(self, target): raise AssertionError("must not inspect")
    creator = Creator(prepared_retry[0], error=AssertionError("must not create"))
    retry = service(
        prepared_retry, creator, BrokenInspector(), BrokenIntegrity()
    ).create_retry_publication(EXECUTION, ATTEMPT_TWO)
    assert retry.execution_id == first.execution_id
    assert retry.acknowledgement is None
    assert creator.calls == []


def test_committed_write_start_is_recovered_without_second_create(prepared_retry):
    with prepared_retry[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_publication_execution_attempts SET status='write_started'"
            " WHERE attempt_number=2"
        ))
    creator = Creator(prepared_retry[0], error=AssertionError("must not create"))
    result = service(prepared_retry, creator).create_retry_publication(
        EXECUTION, ATTEMPT_TWO
    )
    assert result.acknowledgement is None
    assert creator.calls == []


def test_provider_failure_is_detail_free_and_preserves_unknown(prepared_retry):
    creator = Creator(prepared_retry[0], error=TimeoutError("provider detail"))
    with pytest.raises(ReleasePublicationRetryCreateUnavailable) as raised:
        service(prepared_retry, creator).create_retry_publication(
            EXECUTION, ATTEMPT_TWO
        )
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    with prepared_retry[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM release_publication_execution_attempts"
            " WHERE attempt_number=2"
        )) == "outcome_unknown"


def test_visible_target_never_starts_retry_write(prepared_retry):
    with prepared_retry[0].connect() as connection:
        wheel = connection.scalar(text(
            "SELECT wheel_sha256 FROM release_publication_handoffs"
        ))
    inspector = Inspector(ReleasePublicationTargetObservation(
        "artifact-262", "revision-262", "liquent", "1.2.3", wheel, True,
    ))
    creator = Creator(prepared_retry[0])
    assert service(prepared_retry, creator, inspector).create_retry_publication(
        EXECUTION, ATTEMPT_TWO
    ) is None
    assert creator.calls == []


def test_revocation_after_read_before_write_blocks_create(prepared_retry):
    base = Inspector()
    class RevokingInspector:
        def inspect_target(self, target):
            result = base.inspect_target(target)
            with prepared_retry[0].begin() as connection:
                connection.execute(text(
                    "UPDATE release_publication_revision_publishers"
                    " SET status='inactive'"
                ))
            return result
    creator = Creator(prepared_retry[0])
    assert service(
        prepared_retry, creator, RevokingInspector()
    ).create_retry_publication(EXECUTION, ATTEMPT_TWO) is None
    assert creator.calls == []
