from datetime import datetime, timezone

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
    StagingResearchIndexObservation,
    evaluate_staging_research_index_acceptance,
)

RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "a" * 64,
    "https://staging.liquent.ai",
    datetime(2026, 9, 15, tzinfo=timezone.utc),
)


def _observations(outcome=StagingResearchIndexCheckOutcome.PASSED):
    return tuple(
        StagingResearchIndexObservation(check, outcome)
        for check in StagingResearchIndexCheck
    )


def test_complete_passing_set_is_accepted() -> None:
    result = evaluate_staging_research_index_acceptance(RUN, _observations())

    assert result.outcome is StagingResearchIndexAcceptanceOutcome.ACCEPTED
    assert result.run is RUN
    assert not hasattr(result, "cookie")
    assert not hasattr(result, "response_body")


@pytest.mark.parametrize("position", range(len(StagingResearchIndexCheck)))
def test_each_failed_check_rejects(position: int) -> None:
    observations = list(_observations())
    observations[position] = StagingResearchIndexObservation(
        observations[position].check,
        StagingResearchIndexCheckOutcome.FAILED,
    )

    assert evaluate_staging_research_index_acceptance(
        RUN, tuple(observations)
    ).outcome is StagingResearchIndexAcceptanceOutcome.REJECTED


def test_unavailable_check_is_not_rejection_or_acceptance() -> None:
    observations = list(_observations())
    observations[0] = StagingResearchIndexObservation(
        observations[0].check,
        StagingResearchIndexCheckOutcome.UNAVAILABLE,
    )

    assert evaluate_staging_research_index_acceptance(
        RUN, tuple(observations)
    ).outcome is StagingResearchIndexAcceptanceOutcome.UNAVAILABLE


@pytest.mark.parametrize(
    "observations",
    [
        _observations()[:-1],
        _observations() + (_observations()[0],),
        _observations()[:-1] + (_observations()[0],),
    ],
)
def test_missing_duplicate_or_conflicting_shape_rejects(observations) -> None:
    assert evaluate_staging_research_index_acceptance(
        RUN, observations
    ).outcome is StagingResearchIndexAcceptanceOutcome.REJECTED


@pytest.mark.parametrize(
    "digest,origin,observed_at",
    [
        ("latest", "https://staging.liquent.ai", RUN.observed_at),
        ("sha256:" + "A" * 64, "https://staging.liquent.ai", RUN.observed_at),
        (RUN.candidate_digest, "http://staging.liquent.ai", RUN.observed_at),
        (RUN.candidate_digest, "https://user@staging.liquent.ai", RUN.observed_at),
        (RUN.candidate_digest, "https://staging.liquent.ai/research", RUN.observed_at),
        (RUN.candidate_digest, "https://staging.liquent.ai", datetime(2026, 9, 15)),
    ],
)
def test_run_binding_rejects_noncanonical_values(
    digest, origin, observed_at
) -> None:
    with pytest.raises(ValueError):
        StagingResearchIndexAcceptanceRun(digest, origin, observed_at)
