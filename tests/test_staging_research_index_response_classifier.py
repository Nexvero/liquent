from datetime import UTC, datetime

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_request_plan import (
    plan_staging_research_index_requests,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponse,
    classify_staging_research_index_response,
)


def _requests():
    run = StagingResearchIndexAcceptanceRun(
        "sha256:" + "d" * 64, "https://staging.liquent.ai",
        datetime(2026, 9, 15, 10, tzinfo=UTC),
    )
    return plan_staging_research_index_requests(run)


def _html(body: bytes):
    return StagingResearchIndexResponse(200, (("Content-Type", "text/html"),), body)


VISIBLE = (
    b'<h2>Research jobs</h2><ol><li><span>job-visible</span> '
    b'<span>running</span> <time datetime="2026-09-15T10:00:00+00:00">'
    b'2026-09-15T10:00:00+00:00</time></li></ol>'
)


def test_every_planned_response_can_pass_without_retaining_details() -> None:
    responses = (
        StagingResearchIndexResponse(404, (), b""),
        _html(b"No Research jobs are available."),
        _html(VISIBLE),
        _html(VISIBLE),
        StagingResearchIndexResponse(200, (
            ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer")
        ), b""),
        StagingResearchIndexResponse(400, (), b""),
        _html(b"authorized"),
        StagingResearchIndexResponse(404, (), b""),
        StagingResearchIndexResponse(303, (("Location", "/login/unavailable"),), b""),
    )
    classified = tuple(
        classify_staging_research_index_response(request, response)
        for request, response in zip(_requests(), responses, strict=True)
    )
    assert all(item.outcome is StagingResearchIndexCheckOutcome.PASSED for item in classified)
    assert all(set(item.__slots__) == {"check", "phase", "outcome"} for item in classified)


def test_mismatch_is_failed_and_malformed_is_unavailable() -> None:
    request = _requests()[0]
    failed = classify_staging_research_index_response(
        request, StagingResearchIndexResponse(200, (), b"private")
    )
    unavailable = classify_staging_research_index_response(
        request, StagingResearchIndexResponse(404, (("X", "a"), ("x", "b")), b"")
    )
    assert failed.outcome is StagingResearchIndexCheckOutcome.FAILED
    assert unavailable.outcome is StagingResearchIndexCheckOutcome.UNAVAILABLE


def test_minimum_fields_rejects_forbidden_facts() -> None:
    request = next(
        item for item in _requests()
        if item.check is StagingResearchIndexCheck.MINIMUM_FIELDS
    )
    result = classify_staging_research_index_response(request, _html(VISIBLE + b"workspace_id"))
    assert result.outcome is StagingResearchIndexCheckOutcome.FAILED


def test_unavailability_redirect_must_be_detail_free() -> None:
    request = _requests()[-1]
    response = StagingResearchIndexResponse(
        303,
        (("Location", "/login/unavailable"), ("Set-Cookie", "private")),
        b"",
    )
    result = classify_staging_research_index_response(request, response)
    assert result.outcome is StagingResearchIndexCheckOutcome.FAILED
