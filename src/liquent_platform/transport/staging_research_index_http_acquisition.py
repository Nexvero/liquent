"""Bounded single-request acquisition for staging Research-index acceptance."""

import httpx2

from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot,
    StagingResearchIndexRequest,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponse,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    OpaqueStagingResearchSession,
)


_MAX_BODY_BYTES = 65_536


class StagingResearchIndexAcquisitionUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_acquisition_unavailable")


class StagingResearchIndexHttpAcquisition:
    """Acquire one planned response without redirects, retries, or mutation."""

    def __init__(self, client: httpx2.Client) -> None:
        self._client = client

    def acquire(
        self,
        request: StagingResearchIndexRequest,
        session: OpaqueStagingResearchSession | None,
    ) -> StagingResearchIndexResponse:
        try:
            if type(request) is not StagingResearchIndexRequest:
                raise StagingResearchIndexAcquisitionUnavailable
            anonymous = (
                request.credential_slot is StagingResearchIndexCredentialSlot.NONE
            )
            if anonymous != (session is None):
                raise StagingResearchIndexAcquisitionUnavailable
            built = self._client.build_request(
                request.method,
                request.url,
                headers={"Accept": "text/html", "Accept-Encoding": "identity"},
                timeout=httpx2.Timeout(5.0),
            )
            for inherited in ("authorization", "cookie"):
                if inherited in built.headers:
                    del built.headers[inherited]
            if session is not None:
                if type(session) is not OpaqueStagingResearchSession:
                    raise StagingResearchIndexAcquisitionUnavailable
                built.headers["Cookie"] = "liquent_session=" + session.value
            response = self._client.send(
                built, stream=True, follow_redirects=False, auth=None
            )
            try:
                encoding = response.headers.get("content-encoding")
                if encoding is not None and encoding.strip().lower() != "identity":
                    raise StagingResearchIndexAcquisitionUnavailable
                declared = response.headers.get("content-length", "0").strip()
                if not declared.isascii() or not declared.isdigit():
                    raise StagingResearchIndexAcquisitionUnavailable
                if int(declared) > _MAX_BODY_BYTES:
                    raise StagingResearchIndexAcquisitionUnavailable
                chunks = []
                total = 0
                for chunk in response.iter_raw(8192):
                    total += len(chunk)
                    if total > _MAX_BODY_BYTES:
                        raise StagingResearchIndexAcquisitionUnavailable
                    chunks.append(chunk)
                return StagingResearchIndexResponse(
                    response.status_code,
                    tuple(response.headers.multi_items()),
                    b"".join(chunks),
                )
            finally:
                response.close()
        except StagingResearchIndexAcquisitionUnavailable:
            raise
        except Exception:
            raise StagingResearchIndexAcquisitionUnavailable from None
