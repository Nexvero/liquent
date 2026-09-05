import pytest
from sqlalchemy import text

from liquent_platform.identity.release_publication import (
    ReleasePublicationAttemptId,
    ReleasePublicationTargetDecisionKind,
    ReleasePublicationTargetObservation,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationTargetInspectionUnavailable,
)
from liquent_platform.persistence.release_publication_target import (
    DatabaseReleasePublicationTargetInspection,
)
from test_release_publication_artifacts import ATTEMPT, EXECUTION, checker, ready
from test_release_promotion_verifier import signed_candidate


class Inspector:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def inspect_target(self, target):
        self.calls.append(target)
        return self.result


def service(ready, inspector):
    return DatabaseReleasePublicationTargetInspection(
        ready[0], artifact_integrity=checker(ready), target_inspector=inspector,
    )


def observation(**changes):
    values = dict(
        canonical_artifact_id="artifact-256", provider_revision="provider-revision-256",
        package_name="liquent", package_version="1.2.3",
        wheel_sha256="", visible=True,
    )
    values.update(changes)
    return values


def test_absent_target_allows_create_without_mutating_attempt(ready):
    inspector = Inspector()
    result = service(ready, inspector).inspect_publication_target(EXECUTION, ATTEMPT)
    assert result.kind is ReleasePublicationTargetDecisionKind.CREATE_ALLOWED
    assert result.observation is None
    assert result.target.provider_kind == "package-index"
    assert result.target.target_name == "stable"
    assert len(inspector.calls) == 1
    with ready[0].connect() as connection:
        assert connection.execute(text(
            "SELECT status,(SELECT count(*) FROM release_publication_receipts) "
            "FROM release_publication_execution_attempts"
        )).one() == ("prepared", 0)


def test_exact_visible_target_requires_reconciliation_without_create(ready):
    inspector = Inspector(ReleasePublicationTargetObservation(**observation(
        wheel_sha256=ready[0].connect().scalar(text(
            "SELECT wheel_sha256 FROM release_publication_handoffs"
        ))
    )))
    result = service(ready, inspector).inspect_publication_target(EXECUTION, ATTEMPT)
    assert result.kind is ReleasePublicationTargetDecisionKind.RECONCILIATION_REQUIRED
    assert result.observation.canonical_artifact_id == "artifact-256"


@pytest.mark.parametrize("changes", [
    {"wheel_sha256": "0" * 64},
    {"wheel_sha256": "placeholder", "package_version": "9.9.9"},
    {"wheel_sha256": "placeholder", "package_name": "other"},
    {"wheel_sha256": "placeholder", "visible": False},
])
def test_different_or_invisible_existing_target_is_conflict(ready, changes):
    if changes["wheel_sha256"] == "placeholder":
        with ready[0].connect() as connection:
            changes["wheel_sha256"] = connection.scalar(text(
                "SELECT wheel_sha256 FROM release_publication_handoffs"
            ))
    result = service(
        ready, Inspector(ReleasePublicationTargetObservation(**observation(**changes)))
    ).inspect_publication_target(EXECUTION, ATTEMPT)
    assert result.kind is ReleasePublicationTargetDecisionKind.CONFLICT


def test_revoked_publisher_or_pending_reassessment_prevents_inspection(ready):
    inspector = Inspector()
    with ready[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_publication_revision_publishers SET status='inactive'"
        ))
    assert service(ready, inspector).inspect_publication_target(EXECUTION, ATTEMPT) is None
    assert inspector.calls == []


def test_unknown_attempt_prevents_artifact_and_provider_access(ready):
    class BrokenIntegrity:
        def verify_artifacts(self, execution_id, attempt_id):
            return None
    inspector = Inspector()
    subject = DatabaseReleasePublicationTargetInspection(
        ready[0], artifact_integrity=BrokenIntegrity(), target_inspector=inspector,
    )
    assert subject.inspect_publication_target(
        EXECUTION, ReleasePublicationAttemptId("unknown")
    ) is None
    assert inspector.calls == []


def test_provider_unknown_is_detail_free_technical_unavailability(ready):
    class Broken:
        def inspect_target(self, target): raise RuntimeError("provider detail")
    with pytest.raises(ReleasePublicationTargetInspectionUnavailable) as raised:
        service(ready, Broken()).inspect_publication_target(EXECUTION, ATTEMPT)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert str(raised.value) == "release_publication_target_inspection_unavailable"
