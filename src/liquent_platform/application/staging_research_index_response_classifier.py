"""Detail-free classification of bounded staging Research-index responses."""

from dataclasses import dataclass, field
import re

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexRequest,
    StagingResearchIndexRequestPhase,
)


_MAX_BODY_BYTES = 65_536
_INDEX_ENTRY = re.compile(
    rb'<li><span>[^<>]{1,256}</span> <span>'
    rb'(queued|running|succeeded|failed)</span> '
    rb'<time datetime="[^"<>]{1,64}">[^<>]{1,64}</time></li>'
)
_FORBIDDEN_VISIBLE_FACTS = (
    b"user_id", b"workspace_id", b"csrf", b"session", b"membership",
    b"revision", b"claim", b"worker", b"artifact", b"/v1/research/jobs/",
)


@dataclass(frozen=True, slots=True)
class StagingResearchIndexResponse:
    status: int
    headers: tuple[tuple[str, str], ...] = field(repr=False)
    body: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class StagingResearchIndexResponseClassification:
    check: StagingResearchIndexCheck
    phase: StagingResearchIndexRequestPhase
    outcome: StagingResearchIndexCheckOutcome


def _validated(response: StagingResearchIndexResponse) -> tuple[int, dict[str, str], bytes]:
    if (
        type(response) is not StagingResearchIndexResponse
        or isinstance(response.status, bool)
        or not isinstance(response.status, int)
        or not 100 <= response.status <= 599
        or type(response.headers) is not tuple
        or type(response.body) is not bytes
        or len(response.body) > _MAX_BODY_BYTES
    ):
        raise ValueError
    headers: dict[str, str] = {}
    for member in response.headers:
        if type(member) is not tuple or len(member) != 2:
            raise ValueError
        name, value = member
        if type(name) is not str or type(value) is not str:
            raise ValueError
        name = name.strip().lower()
        if not name or name in headers or "\r" in value or "\n" in value:
            raise ValueError
        headers[name] = value.strip()
    return response.status, headers, response.body


def _html(headers: dict[str, str]) -> bool:
    media_type = headers.get("content-type", "").partition(";")[0]
    return media_type.strip().lower() == "text/html"


def _matches(
    request: StagingResearchIndexRequest,
    status: int,
    headers: dict[str, str],
    body: bytes,
) -> bool:
    check = request.check
    if check is StagingResearchIndexCheck.ANONYMOUS_CLOSED:
        return status == 404 and not body
    if check is StagingResearchIndexCheck.AUTHORIZED_EMPTY:
        return (
            status == 200 and _html(headers)
            and b"No Research jobs are available." in body and b"<ol>" not in body
        )
    if check is StagingResearchIndexCheck.AUTHORIZED_VISIBLE:
        return status == 200 and _html(headers) and _INDEX_ENTRY.search(body) is not None
    if check is StagingResearchIndexCheck.MINIMUM_FIELDS:
        lowered = body.lower()
        return (
            status == 200 and _html(headers)
            and _INDEX_ENTRY.search(body) is not None
            and not any(value in lowered for value in _FORBIDDEN_VISIBLE_FACTS)
        )
    if check is StagingResearchIndexCheck.SECURITY_HEADERS:
        return (
            status == 200
            and headers.get("cache-control", "").lower() == "no-store"
            and headers.get("referrer-policy", "").lower() == "no-referrer"
        )
    if check is StagingResearchIndexCheck.QUERY_REJECTED:
        return status == 400 and not body
    if check is StagingResearchIndexCheck.REVOCATION_FRESH:
        if request.phase is StagingResearchIndexRequestPhase.BEFORE_REVOCATION:
            return status == 200 and _html(headers)
        return (
            request.phase is StagingResearchIndexRequestPhase.AFTER_REVOCATION
            and status == 404 and not body
        )
    return (
        check is StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE
        and status == 303 and not body
        and headers.get("location") == "/login/unavailable"
        and "set-cookie" not in headers
    )


def classify_staging_research_index_response(
    request: StagingResearchIndexRequest,
    response: StagingResearchIndexResponse,
) -> StagingResearchIndexResponseClassification:
    """Classify one response without retaining response or diagnostic material."""

    if type(request) is not StagingResearchIndexRequest:
        raise ValueError("planned request is required")
    try:
        status, headers, body = _validated(response)
        outcome = (
            StagingResearchIndexCheckOutcome.PASSED
            if _matches(request, status, headers, body)
            else StagingResearchIndexCheckOutcome.FAILED
        )
    except Exception:
        outcome = StagingResearchIndexCheckOutcome.UNAVAILABLE
    return StagingResearchIndexResponseClassification(
        request.check, request.phase, outcome
    )
