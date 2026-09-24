import json

import pytest

from liquent_platform.application.staging_research_index_promotion_provider_request import (  # noqa: E501
    StagingResearchIndexPromotionProviderStatusRequest,
)
from liquent_platform.transport.staging_research_index_promotion_provider_decoder import (  # noqa: E501
    DecodedStagingResearchIndexPromotionProviderAcquisition,
    RawStagingResearchIndexPromotionProviderResponse,
    StagingResearchIndexPromotionProviderDecodingUnavailable,
)


class Raw:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def acquire_raw(self, request):
        self.calls.append(request)
        return self.response


def _response(status, payload, content_type="application/json"):
    body = payload if type(payload) is bytes else json.dumps(payload).encode()
    return RawStagingResearchIndexPromotionProviderResponse(
        status, (("content-type", content_type),), body
    )


def _request():
    return StagingResearchIndexPromotionProviderStatusRequest("promotion-2721")


def test_exact_pending_and_absent_responses_are_neutral_forms() -> None:
    pending = Raw(_response(202, {
        "operation_id": "promotion-2721", "status": "pending"
    }))
    decoded = DecodedStagingResearchIndexPromotionProviderAcquisition(pending)
    assert decoded.acquire(_request()).operation_id == "promotion-2721"
    absent = Raw(RawStagingResearchIndexPromotionProviderResponse(404, (), b""))
    assert DecodedStagingResearchIndexPromotionProviderAcquisition(
        absent
    ).acquire(_request()) is None


def test_exact_committed_response_is_decoded() -> None:
    payload = {
        "operation_id": "promotion-2721",
        "status": "committed",
        "actor_user_id": "user-2721",
        "evidence_digest": "sha256:" + "a" * 64,
        "candidate_digest": "sha256:" + "b" * 64,
        "staging_origin": "https://staging.liquent.ai",
        "target_environment": "production",
        "observed_at": "2026-09-18T10:00:00Z",
    }
    result = DecodedStagingResearchIndexPromotionProviderAcquisition(
        Raw(_response(200, payload))
    ).acquire(_request())
    assert result.operation_id == "promotion-2721"
    assert result.observed_at.utcoffset() is not None


@pytest.mark.parametrize(
    "response",
    [
        _response(200, {"operation_id": "other", "status": "pending"}),
        _response(202, {"operation_id": "other", "status": "pending"}),
        _response(500, {}),
        _response(200, b"not-json"),
        _response(200, {}, "text/plain"),
        _response(200, b"x" * 16_385),
    ],
)
def test_malformed_or_unexpected_response_fails_closed(response) -> None:
    with pytest.raises(StagingResearchIndexPromotionProviderDecodingUnavailable):
        DecodedStagingResearchIndexPromotionProviderAcquisition(
            Raw(response)
        ).acquire(_request())


def test_raw_failure_is_detail_free() -> None:
    class Broken:
        def acquire_raw(self, _request):
            raise RuntimeError("provider detail")

    with pytest.raises(StagingResearchIndexPromotionProviderDecodingUnavailable) as caught:
        DecodedStagingResearchIndexPromotionProviderAcquisition(Broken()).acquire(
            _request()
        )
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert "provider detail" not in str(caught.value)
