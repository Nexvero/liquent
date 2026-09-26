from datetime import UTC, datetime

import httpx2
import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_request_plan import (
    plan_staging_research_index_requests,
)
from liquent_platform.transport.staging_research_index_http_acquisition import (
    OpaqueStagingResearchSession,
    StagingResearchIndexAcquisitionUnavailable,
    StagingResearchIndexHttpAcquisition,
)


def _requests():
    return plan_staging_research_index_requests(StagingResearchIndexAcceptanceRun(
        "sha256:" + "f" * 64,
        "https://staging.liquent.ai",
        datetime(2026, 9, 15, 12, tzinfo=UTC),
    ))


def test_anonymous_request_removes_inherited_credentials() -> None:
    seen = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(404, content=iter([b""]))

    client = httpx2.Client(
        headers={"Cookie": "inherited=secret", "Authorization": "secret"},
        transport=httpx2.MockTransport(handler),
    )
    result = StagingResearchIndexHttpAcquisition(client).acquire(_requests()[0], None)
    assert result.status == 404
    assert "cookie" not in seen[0].headers
    assert "authorization" not in seen[0].headers


def test_authorized_request_uses_only_opaque_assigned_session() -> None:
    seen = []
    client = httpx2.Client(transport=httpx2.MockTransport(
        lambda request: seen.append(request) or httpx2.Response(
            200, headers={"content-type": "text/html"}, content=iter([b"ok"])
        )
    ))
    session = OpaqueStagingResearchSession("opaque-session-value")
    result = StagingResearchIndexHttpAcquisition(client).acquire(
        _requests()[1], session
    )
    assert result.body == b"ok"
    assert seen[0].headers["cookie"] == "liquent_session=opaque-session-value"
    assert "opaque-session-value" not in repr(session)
    assert "opaque-session-value" not in repr(result)


def test_credential_slot_and_session_must_match() -> None:
    client = httpx2.Client(transport=httpx2.MockTransport(
        lambda _: pytest.fail("request must not be sent")
    ))
    adapter = StagingResearchIndexHttpAcquisition(client)
    session = OpaqueStagingResearchSession("opaque-session-value")
    with pytest.raises(StagingResearchIndexAcquisitionUnavailable):
        adapter.acquire(_requests()[0], session)
    with pytest.raises(StagingResearchIndexAcquisitionUnavailable):
        adapter.acquire(_requests()[1], None)


@pytest.mark.parametrize(
    "response",
    (
        httpx2.Response(
            200, headers={"content-encoding": "gzip"}, content=iter([b"x"])
        ),
        httpx2.Response(
            200, headers={"content-length": "65537"}, content=iter([b""])
        ),
        httpx2.Response(200, content=iter([b"x" * 65_537])),
    ),
)
def test_unbounded_or_encoded_response_is_detail_free_unavailable(response) -> None:
    client = httpx2.Client(transport=httpx2.MockTransport(lambda _: response))
    adapter = StagingResearchIndexHttpAcquisition(client)
    with pytest.raises(StagingResearchIndexAcquisitionUnavailable) as caught:
        adapter.acquire(_requests()[0], None)
    assert str(caught.value) == "staging_research_index_acquisition_unavailable"


def test_transport_detail_is_not_reflected() -> None:
    def unavailable(request):
        raise httpx2.ConnectError("private provider detail", request=request)

    client = httpx2.Client(transport=httpx2.MockTransport(unavailable))
    with pytest.raises(StagingResearchIndexAcquisitionUnavailable) as caught:
        StagingResearchIndexHttpAcquisition(client).acquire(_requests()[0], None)
    assert "private" not in str(caught.value)
