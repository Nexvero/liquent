"""Bounded single-request HTTP acquisition for promotion provider status."""

from urllib.parse import urlsplit

import httpx2

from liquent_platform.application.staging_research_index_promotion_provider_request import (  # noqa: E501
    StagingResearchIndexPromotionProviderStatusRequest,
)
from liquent_platform.transport.staging_research_index_promotion_provider_decoder import (  # noqa: E501
    RawStagingResearchIndexPromotionProviderResponse,
)


_MAX_BODY_BYTES = 16_384


class StagingResearchIndexPromotionProviderHttpUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_provider_http_unavailable")


class StagingResearchIndexPromotionProviderHttpAcquisition:
    __slots__ = ("_client", "_endpoint")

    def __init__(self, client: httpx2.Client, endpoint: str) -> None:
        parsed = urlsplit(endpoint)
        if (
            type(client) is not httpx2.Client
            or type(endpoint) is not str
            or parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or not parsed.path.endswith("/")
        ):
            raise StagingResearchIndexPromotionProviderHttpUnavailable
        self._client = client
        self._endpoint = endpoint

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionProviderHttpAcquisition()"

    def acquire_raw(
        self, request: StagingResearchIndexPromotionProviderStatusRequest
    ) -> RawStagingResearchIndexPromotionProviderResponse:
        try:
            if type(request) is not StagingResearchIndexPromotionProviderStatusRequest:
                raise StagingResearchIndexPromotionProviderHttpUnavailable
            built = self._client.build_request(
                "GET",
                self._endpoint + request.operation_id,
                headers={"Accept": "application/json", "Accept-Encoding": "identity"},
                timeout=httpx2.Timeout(5.0),
            )
            for inherited in ("authorization", "cookie"):
                if inherited in built.headers:
                    del built.headers[inherited]
            response = self._client.send(
                built, stream=True, follow_redirects=False, auth=None
            )
            try:
                encoding = response.headers.get("content-encoding")
                if encoding is not None and encoding.strip().lower() != "identity":
                    raise StagingResearchIndexPromotionProviderHttpUnavailable
                declared = response.headers.get("content-length")
                if declared is not None:
                    value = declared.strip()
                    if not value.isascii() or not value.isdigit():
                        raise StagingResearchIndexPromotionProviderHttpUnavailable
                    if int(value) > _MAX_BODY_BYTES:
                        raise StagingResearchIndexPromotionProviderHttpUnavailable
                chunks = []
                total = 0
                for chunk in response.iter_raw(4096):
                    total += len(chunk)
                    if total > _MAX_BODY_BYTES:
                        raise StagingResearchIndexPromotionProviderHttpUnavailable
                    chunks.append(chunk)
                return RawStagingResearchIndexPromotionProviderResponse(
                    response.status_code,
                    tuple(response.headers.multi_items()),
                    b"".join(chunks),
                )
            finally:
                response.close()
        except StagingResearchIndexPromotionProviderHttpUnavailable:
            raise
        except Exception:
            raise StagingResearchIndexPromotionProviderHttpUnavailable from None
