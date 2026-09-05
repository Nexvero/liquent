import pytest
from sqlalchemy import text

from liquent_platform.identity.release_publication import (
    ReleasePublicationCreateAcknowledgement,
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.identity_errors import ReleasePublicationCreateUnavailable
from liquent_platform.persistence.release_publication_create import DatabaseReleasePublicationImmutableCreate
from liquent_platform.persistence.release_publication_target import DatabaseReleasePublicationTargetInspection
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, checker, ready
from test_release_publication_target import Inspector


class Creator:
    def __init__(self, engine, result=None, error=None):
        self.engine = engine
        self.result = result or ReleasePublicationCreateAcknowledgement("request-257")
        self.error = error
        self.calls = []

    def create_immutable(self, target, artifacts, idempotency_key):
        with self.engine.connect() as connection:
            state = connection.execute(text(
                "SELECT execution.status,attempt.status FROM release_publication_executions execution"
                " JOIN release_publication_execution_attempts attempt"
                " ON attempt.execution_id=execution.execution_id"
            )).one()
        assert state == ("prepared", "write_started")
        self.calls.append((target, artifacts, idempotency_key))
        if self.error:
            raise self.error
        return self.result


def target_inspection(ready, inspector=None):
    return DatabaseReleasePublicationTargetInspection(
        ready[0], artifact_integrity=checker(ready),
        target_inspector=inspector or Inspector(),
    )


def create_service(ready, creator, inspection=None):
    return DatabaseReleasePublicationImmutableCreate(
        ready[0], target_inspection=inspection or target_inspection(ready),
        immutable_creator=creator,
    )


def test_commits_write_start_before_one_create_then_marks_unknown(ready):
    creator = Creator(ready[0])
    result = create_service(ready, creator).create_publication(EXECUTION, ATTEMPT)
    assert result.acknowledgement.provider_request_id == "request-257"
    assert len(creator.calls) == 1
    assert creator.calls[0][2] == EXECUTION
    with ready[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status,attempt.finished_at "
            "FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("outcome_unknown", "outcome_unknown", None)
        assert connection.scalar(text("SELECT count(*) FROM release_publication_receipts")) == 0


def test_retry_of_possible_effect_never_inspects_or_creates_again(ready):
    first_creator = Creator(ready[0])
    first = create_service(ready, first_creator).create_publication(EXECUTION, ATTEMPT)
    class Broken:
        def inspect_publication_target(self, execution_id, attempt_id):
            raise AssertionError("must not inspect")
    second_creator = Creator(ready[0], error=AssertionError("must not create"))
    retry = create_service(ready, second_creator, Broken()).create_publication(EXECUTION, ATTEMPT)
    assert retry.execution_id == first.execution_id
    assert retry.acknowledgement is None
    assert second_creator.calls == []


def test_retry_recovers_committed_write_started_as_unknown_without_create(ready):
    with ready[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_publication_execution_attempts SET status='write_started'"
        ))
    class Broken:
        def inspect_publication_target(self, execution_id, attempt_id):
            raise AssertionError("must not inspect")
    creator = Creator(ready[0], error=AssertionError("must not create"))
    result = create_service(ready, creator, Broken()).create_publication(EXECUTION, ATTEMPT)
    assert result.acknowledgement is None
    assert creator.calls == []
    with ready[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("outcome_unknown", "outcome_unknown")


def test_provider_failure_is_persisted_unknown_and_detail_free(ready):
    creator = Creator(ready[0], error=TimeoutError("provider timeout detail"))
    with pytest.raises(ReleasePublicationCreateUnavailable) as raised:
        create_service(ready, creator).create_publication(EXECUTION, ATTEMPT)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    with ready[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("outcome_unknown", "outcome_unknown")


def test_existing_target_conflict_never_starts_write(ready):
    with ready[0].connect() as connection:
        wheel = connection.scalar(text("SELECT wheel_sha256 FROM release_publication_handoffs"))
    inspection = target_inspection(ready, Inspector(ReleasePublicationTargetObservation(
        "artifact-257", "revision-257", "liquent", "1.2.3", "0" * 64, True,
    )))
    creator = Creator(ready[0])
    assert create_service(ready, creator, inspection).create_publication(EXECUTION, ATTEMPT) is None
    assert creator.calls == []
    with ready[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM release_publication_execution_attempts"
        )) == "prepared"


def test_revocation_after_inspection_blocks_write_start(ready):
    base = target_inspection(ready)
    class RevokingInspection:
        def inspect_publication_target(self, execution_id, attempt_id):
            result = base.inspect_publication_target(execution_id, attempt_id)
            with ready[0].begin() as connection:
                connection.execute(text(
                    "UPDATE release_publication_revision_publishers SET status='inactive'"
                ))
            return result
    creator = Creator(ready[0])
    assert create_service(ready, creator, RevokingInspection()).create_publication(
        EXECUTION, ATTEMPT
    ) is None
    assert creator.calls == []


def test_invalid_provider_acknowledgement_still_preserves_unknown(ready):
    creator = Creator(ready[0], result="invalid")
    with pytest.raises(ReleasePublicationCreateUnavailable):
        create_service(ready, creator).create_publication(EXECUTION, ATTEMPT)
    with ready[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM release_publication_execution_attempts"
        )) == "outcome_unknown"
