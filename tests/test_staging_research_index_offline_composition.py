from datetime import UTC, datetime

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_offline_composition import (
    evaluate_staging_research_index_responses,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponse,
)


RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "e" * 64,
    "https://staging.liquent.ai",
    datetime(2026, 9, 15, 11, tzinfo=UTC),
)
VISIBLE = (
    b'<li><span>opaque-job</span> <span>running</span> '
    b'<time datetime="2026-09-15T11:00:00+00:00">'
    b'2026-09-15T11:00:00+00:00</time></li>'
)


def _html(body):
    return StagingResearchIndexResponse(200, (("content-type", "text/html"),), body)


def _passing():
    return (
        StagingResearchIndexResponse(404, (), b""),
        _html(b"No Research jobs are available."),
        _html(VISIBLE),
        _html(VISIBLE),
        StagingResearchIndexResponse(200, (
            ("cache-control", "no-store"), ("referrer-policy", "no-referrer")
        ), b""),
        StagingResearchIndexResponse(400, (), b""),
        _html(b"authorized"),
        StagingResearchIndexResponse(404, (), b""),
        StagingResearchIndexResponse(303, (("location", "/login/unavailable"),), b""),
    )


def test_complete_passing_response_set_is_accepted() -> None:
    result = evaluate_staging_research_index_responses(RUN, _passing())
    assert result.run is RUN
    assert result.outcome is StagingResearchIndexAcceptanceOutcome.ACCEPTED


def test_valid_mismatch_is_rejected() -> None:
    responses = list(_passing())
    responses[0] = StagingResearchIndexResponse(200, (), b"private")
    result = evaluate_staging_research_index_responses(RUN, tuple(responses))
    assert result.outcome is StagingResearchIndexAcceptanceOutcome.REJECTED


def test_malformed_response_is_unavailable() -> None:
    responses = list(_passing())
    responses[0] = StagingResearchIndexResponse(404, (("x", "a"), ("X", "b")), b"")
    result = evaluate_staging_research_index_responses(RUN, tuple(responses))
    assert result.outcome is StagingResearchIndexAcceptanceOutcome.UNAVAILABLE


@pytest.mark.parametrize("responses", ((), _passing()[:-1], (*_passing(), _passing()[0])))
def test_non_exact_response_cardinality_is_rejected(responses) -> None:
    with pytest.raises(ValueError):
        evaluate_staging_research_index_responses(RUN, responses)


def test_list_is_not_an_offline_response_set() -> None:
    with pytest.raises(ValueError):
        evaluate_staging_research_index_responses(RUN, list(_passing()))
