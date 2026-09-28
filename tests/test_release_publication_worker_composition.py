import json
from datetime import timedelta
from pathlib import Path

import httpx2
from sqlalchemy import text

from liquent_platform.identity.release_authority import ReleasePromotionVerifierId
from liquent_platform.identity.release_publication import (
    ReleasePublicationAttemptId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationExecutorId,
    ReleasePublicationHandoffId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
    ReleasePublicationWorkRequest,
    ReleasePublicationWorkResultKind,
    ReleasePublisherAuthorityId,
)
from liquent_platform.identity.release_publication_provider import (
    PackageIndexHttpPolicy,
)
from liquent_platform.operators.release_publication_worker_composition import (
    ReleasePublicationWorkerComposition,
    compose_release_publication_worker,
)
from liquent_platform.persistence.release_publication_artifacts import (
    BoundLocalReleasePublicationArtifactSource,
)
from liquent_platform.transport.package_index_composition import (
    compose_package_index_publication,
)
from test_release_promotion_verifier import DECISION_TIME, signed_candidate
from test_release_publication_artifacts import EXECUTION, ready


POLICY = PackageIndexHttpPolicy(
    timedelta(seconds=1),
    timedelta(seconds=1),
    timedelta(seconds=2),
    4096,
    16 * 1024 * 1024,
)
NOW = DECISION_TIME


def _credential(tmp_path: Path) -> Path:
    path = tmp_path / "package-index-worker-credential"
    path.write_text("worker-token\n")
    path.chmod(0o600)
    return path


def _request(ready):
    with ready[0].connect() as connection:
        row = connection.execute(text(
            "SELECT handoff_id,publisher_authority_id,channel_id,"
            " channel_revision_id FROM release_publication_executions"
        )).one()
    return ReleasePublicationWorkRequest(
        EXECUTION,
        ReleasePublicationHandoffId(bytes(row.handoff_id).decode()),
        ReleasePublisherAuthorityId(bytes(row.publisher_authority_id).decode()),
        ReleasePublicationChannelId(bytes(row.channel_id).decode()),
        ReleasePublicationChannelPolicyRevisionId(
            bytes(row.channel_revision_id).decode()
        ),
    )


def _compose(ready, tmp_path, handler):
    clients = []

    def factory(**arguments):
        client = httpx2.Client(
            transport=httpx2.MockTransport(handler), **arguments
        )
        clients.append(client)
        return client

    provider = compose_package_index_publication(
        origin="https://packages.example",
        target_name="stable",
        credential_path=_credential(tmp_path),
        policy=POLICY,
        client_factory=factory,
    )
    evidence = json.loads(ready[2].read_text())
    source = BoundLocalReleasePublicationArtifactSource({ready[3]: ready[4]})
    composition = compose_release_publication_worker(
        engine=ready[0],
        provider=provider,
        artifact_source=source,
        executor_id=ReleasePublicationExecutorId("executor-255"),
        promotion_verifier_id=ReleasePromotionVerifierId(
            evidence["verification_identity"]
        ),
        generate_attempt_id=lambda: ReleasePublicationAttemptId(
            "attempt-generated-lq273"
        ),
        generate_receipt_id=lambda: ReleasePublicationProviderReceiptId(
            "receipt-lq273"
        ),
        generate_recovery_id=lambda: ReleasePublicationRecoveryId(
            "recovery-lq273"
        ),
        generate_reassessment_id=lambda: ReleasePublicationReassessmentId(
            "reassessment-lq273"
        ),
        clock=lambda: NOW,
    )
    return composition, clients


def test_composition_builds_without_database_or_provider_io(ready, tmp_path):
    def unexpected(_):
        raise AssertionError("composition performed provider I/O")

    composition, clients = _compose(ready, tmp_path, unexpected)
    assert type(composition) is ReleasePublicationWorkerComposition
    assert repr(composition) == "ReleasePublicationWorkerComposition()"
    assert repr(composition.worker) == "ProcessReleasePublicationWork()"
    assert not clients[0].is_closed
    composition.close()
    assert clients[0].is_closed
    composition.close()


def test_complete_composition_publishes_with_one_create_and_readback(
    ready, tmp_path
):
    with ready[0].connect() as connection:
        wheel = connection.scalar(text(
            "SELECT wheel_sha256 FROM release_publication_handoffs"
        ))
    calls = []

    def handler(request):
        calls.append(request.method)
        assert request.headers["authorization"] == "Bearer worker-token"
        if request.method == "GET" and "PUT" not in calls:
            return httpx2.Response(404, content=iter([b""]))
        if request.method == "PUT":
            return httpx2.Response(
                201,
                headers={"content-type": "application/json"},
                content=iter([b'{"provider_request_id":"request-lq273"}']),
            )
        body = json.dumps({
            "canonical_artifact_id": "artifact-lq273",
            "provider_revision": "provider-revision-lq273",
            "package_name": "liquent",
            "package_version": "1.2.3",
            "wheel_sha256": wheel,
            "visible": True,
        }).encode()
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=iter([body]),
        )

    composition, clients = _compose(ready, tmp_path, handler)
    with composition:
        result = composition.worker.process(_request(ready))
        assert result.kind is ReleasePublicationWorkResultKind.PUBLISHED
        assert calls == ["GET", "PUT", "GET"]
    assert clients[0].is_closed
    with ready[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM release_publication_executions"
        )) == "published"


def test_context_closes_resources_when_work_raises(ready, tmp_path):
    def broken(_):
        raise RuntimeError("provider-private-detail")

    composition, clients = _compose(ready, tmp_path, broken)
    try:
        with composition:
            composition.worker.process(_request(ready))
    except Exception:
        pass
    assert clients[0].is_closed
