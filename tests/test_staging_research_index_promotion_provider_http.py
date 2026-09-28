import httpx2
import pytest

from liquent_platform.application.staging_research_index_promotion_provider_request import (  # noqa: E501
    StagingResearchIndexPromotionProviderStatusRequest,
)
from liquent_platform.transport.staging_research_index_promotion_provider_http import (  # noqa: E501
    StagingResearchIndexPromotionProviderHttpAcquisition,
    StagingResearchIndexPromotionProviderHttpUnavailable,
)


def _request():
    return StagingResearchIndexPromotionProviderStatusRequest("promotion-2722")


def test_exact_get_removes_inherited_credentials_and_reads_once() -> None:
    seen = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(
            202,
            headers={"content-type": "application/json"},
            content=iter([b'{"status":"pending"}']),
        )

    client = httpx2.Client(
        headers={"Cookie": "secret", "Authorization": "secret"},
        transport=httpx2.MockTransport(handler),
    )
    adapter = StagingResearchIndexPromotionProviderHttpAcquisition(
        client, "https://provider.example/status/"
    )
    result = adapter.acquire_raw(_request())
    assert result.status == 202
    assert result.body == b'{"status":"pending"}'
    assert len(seen) == 1
    assert str(seen[0].url) == "https://provider.example/status/promotion-2722"
    assert seen[0].method == "GET"
    assert "authorization" not in seen[0].headers
    assert "cookie" not in seen[0].headers
    assert seen[0].headers["accept-encoding"] == "identity"
    assert repr(adapter) == "StagingResearchIndexPromotionProviderHttpAcquisition()"


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://provider.example/status/",
        "https://user@provider.example/status/",
        "https://provider.example/status",
        "https://provider.example/status/?query=1",
    ],
)
def test_invalid_endpoint_is_rejected(endpoint) -> None:
    with pytest.raises(StagingResearchIndexPromotionProviderHttpUnavailable):
        StagingResearchIndexPromotionProviderHttpAcquisition(
            httpx2.Client(), endpoint
        )


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(200, headers={"content-encoding": "gzip"}, content=b"x"),
        httpx2.Response(200, headers={"content-length": "16385"}, content=b""),
        httpx2.Response(200, content=iter([b"x" * 16_385])),
    ],
)
def test_encoded_or_excessive_response_fails_closed(response) -> None:
    client = httpx2.Client(transport=httpx2.MockTransport(lambda _: response))
    adapter = StagingResearchIndexPromotionProviderHttpAcquisition(
        client, "https://provider.example/status/"
    )
    with pytest.raises(StagingResearchIndexPromotionProviderHttpUnavailable):
        adapter.acquire_raw(_request())


def test_transport_failure_is_detail_free_and_has_no_retry() -> None:
    def broken(request):
        raise httpx2.ConnectError("private detail", request=request)

    adapter = StagingResearchIndexPromotionProviderHttpAcquisition(
        httpx2.Client(transport=httpx2.MockTransport(broken)),
        "https://provider.example/status/",
    )
    with pytest.raises(StagingResearchIndexPromotionProviderHttpUnavailable) as caught:
        adapter.acquire_raw(_request())
    assert "private detail" not in str(caught.value)
    assert not hasattr(adapter, "retry")
    assert not hasattr(adapter, "promote")
