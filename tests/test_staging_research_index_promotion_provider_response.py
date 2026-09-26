from dataclasses import replace

import pytest

from liquent_platform.adapters.staging_research_index_promotion_provider_response import (  # noqa: E501
    ClassifiedStagingResearchIndexPromotionStatusGateway,
    CommittedStagingResearchIndexPromotionProviderResponse,
    PendingStagingResearchIndexPromotionProviderResponse,
    StagingResearchIndexPromotionProviderResponseUnavailable,
)
from tests.test_staging_research_index_promotion_attempt_journal import NOW
from tests.test_staging_research_index_promotion_reconciliation import _unknown


class Transport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def read_operation(self, operation_id):
        self.calls.append(operation_id)
        return self.response


def _committed(unknown):
    prepared = unknown.attempt.prepared
    return CommittedStagingResearchIndexPromotionProviderResponse(
        prepared.operation_id,
        prepared.command.actor.user_id,
        prepared.command.evidence_digest,
        prepared.authority.candidate_digest,
        prepared.authority.staging_origin,
        prepared.authority.target_environment,
        NOW,
    )


def test_exact_committed_response_is_classified() -> None:
    unknown = _unknown()
    operation_id = unknown.attempt.prepared.operation_id
    transport = Transport(_committed(unknown))
    gateway = ClassifiedStagingResearchIndexPromotionStatusGateway(transport)
    status = gateway.read_committed(operation_id)
    assert status is not None
    assert status.operation_id == operation_id
    assert transport.calls == [operation_id]
    assert repr(gateway) == "ClassifiedStagingResearchIndexPromotionStatusGateway()"


@pytest.mark.parametrize("response", [None, "pending"])
def test_absent_or_matching_pending_response_is_neutral(response) -> None:
    operation_id = _unknown().attempt.prepared.operation_id
    value = (
        PendingStagingResearchIndexPromotionProviderResponse(operation_id)
        if response == "pending"
        else None
    )
    assert ClassifiedStagingResearchIndexPromotionStatusGateway(
        Transport(value)
    ).read_committed(operation_id) is None


def test_substituted_response_fails_closed() -> None:
    unknown = _unknown()
    operation_id = unknown.attempt.prepared.operation_id
    for response in (
        PendingStagingResearchIndexPromotionProviderResponse("substituted"),
        replace(_committed(unknown), operation_id="substituted"),
    ):
        with pytest.raises(StagingResearchIndexPromotionProviderResponseUnavailable):
            ClassifiedStagingResearchIndexPromotionStatusGateway(
                Transport(response)
            ).read_committed(operation_id)


def test_transport_failure_is_detail_free_and_read_only() -> None:
    class Broken:
        def read_operation(self, _operation_id):
            raise RuntimeError("transport detail")

    gateway = ClassifiedStagingResearchIndexPromotionStatusGateway(Broken())
    with pytest.raises(StagingResearchIndexPromotionProviderResponseUnavailable) as caught:
        gateway.read_committed("promotion-2719")
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "transport detail" not in str(caught.value)
    assert not hasattr(gateway, "promote")
    assert not hasattr(gateway, "retry")
