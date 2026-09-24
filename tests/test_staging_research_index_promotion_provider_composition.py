import json

import httpx2
import pytest

from liquent_platform.transport.staging_research_index_promotion_provider_composition import (  # noqa: E501
    StagingResearchIndexPromotionProviderCompositionUnavailable,
    compose_staging_research_index_promotion_provider_observer,
)
from tests.test_staging_research_index_promotion_reconciliation import _unknown


def _payload(unknown):
    prepared = unknown.attempt.prepared
    return {
        "operation_id": prepared.operation_id,
        "status": "committed",
        "actor_user_id": prepared.command.actor.user_id,
        "evidence_digest": prepared.command.evidence_digest,
        "candidate_digest": prepared.authority.candidate_digest,
        "staging_origin": prepared.authority.staging_origin,
        "target_environment": prepared.authority.target_environment,
        "observed_at": "2026-09-18T10:00:00Z",
    }


def test_composed_observer_reads_and_binds_one_committed_outcome() -> None:
    unknown = _unknown()
    seen = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=iter([json.dumps(_payload(unknown)).encode()]),
        )

    client = httpx2.Client(transport=httpx2.MockTransport(handler))
    observer = compose_staging_research_index_promotion_provider_observer(
        client, "https://provider.example/status/"
    )
    observation = observer.observe_committed(unknown)
    assert observation is not None
    assert observation.receipt.operation_id == unknown.attempt.prepared.operation_id
    assert len(seen) == 1


def test_composed_observer_preserves_pending_as_neutral() -> None:
    unknown = _unknown()
    operation_id = unknown.attempt.prepared.operation_id
    response = {
        "operation_id": operation_id,
        "status": "pending",
    }
    client = httpx2.Client(transport=httpx2.MockTransport(
        lambda _: httpx2.Response(
            202,
            headers={"content-type": "application/json"},
            content=iter([json.dumps(response).encode()]),
        )
    ))
    observer = compose_staging_research_index_promotion_provider_observer(
        client, "https://provider.example/status/"
    )
    assert observer.observe_committed(unknown) is None


def test_invalid_wiring_is_detail_free() -> None:
    with pytest.raises(
        StagingResearchIndexPromotionProviderCompositionUnavailable
    ) as caught:
        compose_staging_research_index_promotion_provider_observer(
            httpx2.Client(), "http://provider.example/status/"
        )
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_composition_does_not_own_client_or_add_mutation() -> None:
    client = httpx2.Client(transport=httpx2.MockTransport(
        lambda _: httpx2.Response(404, content=b"")
    ))
    observer = compose_staging_research_index_promotion_provider_observer(
        client, "https://provider.example/status/"
    )
    assert not client.is_closed
    assert not hasattr(observer, "promote")
    assert not hasattr(observer, "retry")
    client.close()
