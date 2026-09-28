from dataclasses import replace

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceResult,
)
from liquent_platform.application.staging_research_index_promotion_eligibility import (
    StagingResearchIndexPromotionEligibility,
    evaluate_staging_research_index_promotion_eligibility,
)
from tests.test_staging_research_index_acceptance_operator import RUN


def test_accepted_result_produces_non_authorizing_eligibility() -> None:
    result = StagingResearchIndexAcceptanceResult(
        RUN, StagingResearchIndexAcceptanceOutcome.ACCEPTED
    )
    eligibility = evaluate_staging_research_index_promotion_eligibility(result)
    assert type(eligibility) is StagingResearchIndexPromotionEligibility
    assert eligibility.run is RUN


@pytest.mark.parametrize(
    "outcome",
    [
        StagingResearchIndexAcceptanceOutcome.REJECTED,
        StagingResearchIndexAcceptanceOutcome.UNAVAILABLE,
    ],
)
def test_non_accepted_outcomes_are_neutral(
    outcome: StagingResearchIndexAcceptanceOutcome,
) -> None:
    assert evaluate_staging_research_index_promotion_eligibility(
        StagingResearchIndexAcceptanceResult(RUN, outcome)
    ) is None


def test_absent_invocation_result_is_neutral() -> None:
    assert evaluate_staging_research_index_promotion_eligibility(None) is None


def test_substituted_result_shape_is_rejected() -> None:
    accepted = StagingResearchIndexAcceptanceResult(
        RUN, StagingResearchIndexAcceptanceOutcome.ACCEPTED
    )
    substituted = replace(accepted, outcome="accepted")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exact staging acceptance result"):
        evaluate_staging_research_index_promotion_eligibility(substituted)
    with pytest.raises(ValueError, match="exact staging acceptance result"):
        evaluate_staging_research_index_promotion_eligibility(object())  # type: ignore[arg-type]


def test_representation_hides_candidate_and_origin() -> None:
    eligibility = evaluate_staging_research_index_promotion_eligibility(
        StagingResearchIndexAcceptanceResult(
            RUN, StagingResearchIndexAcceptanceOutcome.ACCEPTED
        )
    )
    assert repr(eligibility) == "StagingResearchIndexPromotionEligibility()"
    assert RUN.candidate_digest not in repr(eligibility)
    assert RUN.staging_origin not in repr(eligibility)
    assert not hasattr(eligibility, "promote")
    assert not hasattr(eligibility, "authority")
