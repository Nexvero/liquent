from sqlalchemy import text

from liquent_platform.identity.release_publication_provider import (
    PackageIndexCreateRecord,
    PackageIndexProviderConfiguration,
)
from liquent_platform.identity.release_publication_package_index import (
    PackageIndexReleasePublicationAdapter,
)
from liquent_platform.persistence.release_publication_create import (
    DatabaseReleasePublicationImmutableCreate,
)
from liquent_platform.persistence.release_publication_target import (
    DatabaseReleasePublicationTargetInspection,
)
from test_release_promotion_verifier import signed_candidate
from test_release_publication_artifacts import ATTEMPT, EXECUTION, checker, ready


class Transport:
    def __init__(self):
        self.inspect_calls = 0
        self.create_keys = []

    def inspect_package(self, configuration, target):
        self.inspect_calls += 1
        return None

    def create_package(self, configuration, target, artifacts, idempotency_key):
        self.create_keys.append(idempotency_key)
        return PackageIndexCreateRecord("request-integration-267")


def test_controlled_package_index_create_preserves_unknown_outcome(ready):
    transport = Transport()
    adapter = PackageIndexReleasePublicationAdapter(
        PackageIndexProviderConfiguration(
            "https://packages.example.test", "stable", "secret-token"
        ),
        transport,
    )
    result = DatabaseReleasePublicationImmutableCreate(
        ready[0],
        target_inspection=DatabaseReleasePublicationTargetInspection(
            ready[0], artifact_integrity=checker(ready),
            target_inspector=adapter,
        ),
        immutable_creator=adapter,
    ).create_publication(EXECUTION, ATTEMPT)
    assert result.acknowledgement.provider_request_id == "request-integration-267"
    assert transport.inspect_calls == 1
    assert transport.create_keys == [EXECUTION.value]
    with ready[0].connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status"
            " FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("outcome_unknown", "outcome_unknown")
