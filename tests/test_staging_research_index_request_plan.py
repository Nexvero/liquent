from datetime import UTC, datetime

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot,
    StagingResearchIndexRequestPhase,
    plan_staging_research_index_requests,
)


def _run():
    return StagingResearchIndexAcceptanceRun(
        "sha256:" + "c" * 64,
        "https://staging.liquent.ai",
        datetime(2026, 9, 15, 9, tzinfo=UTC),
    )


def test_plan_is_complete_ordered_and_exact() -> None:
    requests = plan_staging_research_index_requests(_run())
    assert tuple(request.check for request in requests) == (
        *tuple(StagingResearchIndexCheck)[:-2],
        StagingResearchIndexCheck.REVOCATION_FRESH,
        StagingResearchIndexCheck.REVOCATION_FRESH,
        StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE,
    )
    assert tuple(request.sequence for request in requests) == tuple(range(1, 10))
    assert {request.method for request in requests} == {"GET"}
    assert all(request.url.startswith("https://staging.liquent.ai/research") for request in requests)
    assert requests[5].url == "https://staging.liquent.ai/research?workspace=probe"
    assert all("@" not in request.url for request in requests)
    assert tuple(request.phase for request in requests[6:8]) == (
        StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
        StagingResearchIndexRequestPhase.AFTER_REVOCATION,
    )


def test_anonymous_and_query_requests_have_no_credential() -> None:
    requests = plan_staging_research_index_requests(_run())
    slots = {request.check: request.credential_slot for request in requests}
    assert (
        slots[StagingResearchIndexCheck.ANONYMOUS_CLOSED]
        is StagingResearchIndexCredentialSlot.NONE
    )
    assert (
        slots[StagingResearchIndexCheck.QUERY_REJECTED]
        is StagingResearchIndexCredentialSlot.NONE
    )


def test_plan_carries_no_authority_or_transport_material() -> None:
    fields = set(requests_field.name for requests_field in requests_dataclass_fields())
    assert fields == {
        "check", "sequence", "method", "url", "credential_slot", "phase"
    }
    assert not fields & {"allow", "role", "token", "cookie", "workspace_id", "headers", "body"}


def requests_dataclass_fields():
    from dataclasses import fields
    from liquent_platform.application.staging_research_index_request_plan import StagingResearchIndexRequest
    return fields(StagingResearchIndexRequest)


def test_plan_rejects_unbound_input() -> None:
    with pytest.raises(ValueError):
        plan_staging_research_index_requests(object())
