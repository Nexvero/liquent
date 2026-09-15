from dataclasses import replace
from datetime import UTC, datetime

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexRequestPhase,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponseClassification,
)
from liquent_platform.application.staging_research_index_stage_handoff import (
    StagingResearchIndexStageHandoff,
    evaluate_staging_research_index_handoffs,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    StagingResearchIndexAcquisitionStage,
)


RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "2" * 64,
    "https://staging.liquent.ai",
    datetime(2026, 9, 15, 14, tzinfo=UTC),
)


def _classification(check, phase, outcome=StagingResearchIndexCheckOutcome.PASSED):
    return StagingResearchIndexResponseClassification(check, phase, outcome)


def _handoffs(run=RUN):
    baseline = tuple(
        _classification(check, StagingResearchIndexRequestPhase.SINGLE)
        for check in StagingResearchIndexCheck
        if check not in {
            StagingResearchIndexCheck.REVOCATION_FRESH,
            StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE,
        }
    ) + (_classification(
        StagingResearchIndexCheck.REVOCATION_FRESH,
        StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
    ),)
    return (
        StagingResearchIndexStageHandoff(
            run, StagingResearchIndexAcquisitionStage.BASELINE, baseline
        ),
        StagingResearchIndexStageHandoff(
            run,
            StagingResearchIndexAcquisitionStage.AFTER_REVOCATION,
            (_classification(
                StagingResearchIndexCheck.REVOCATION_FRESH,
                StagingResearchIndexRequestPhase.AFTER_REVOCATION,
            ),),
        ),
        StagingResearchIndexStageHandoff(
            run,
            StagingResearchIndexAcquisitionStage.UNAVAILABILITY,
            (_classification(
                StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE,
                StagingResearchIndexRequestPhase.SINGLE,
            ),),
        ),
    )


def test_exact_same_run_handoffs_are_evaluated() -> None:
    result = evaluate_staging_research_index_handoffs(_handoffs())
    assert result.run is RUN
    assert result.outcome is StagingResearchIndexAcceptanceOutcome.ACCEPTED


def test_handoff_order_is_not_caller_authority() -> None:
    handoffs = _handoffs()
    result = evaluate_staging_research_index_handoffs(tuple(reversed(handoffs)))
    assert result.outcome is StagingResearchIndexAcceptanceOutcome.ACCEPTED


def test_different_run_binding_is_rejected() -> None:
    handoffs = list(_handoffs())
    another = replace(RUN, candidate_digest="sha256:" + "3" * 64)
    handoffs[1] = replace(handoffs[1], run=another)
    with pytest.raises(ValueError):
        evaluate_staging_research_index_handoffs(tuple(handoffs))


@pytest.mark.parametrize("mutation", ("missing", "duplicate"))
def test_non_exact_handoff_set_is_rejected(mutation) -> None:
    handoffs = list(_handoffs())
    if mutation == "missing":
        handoffs.pop()
    else:
        handoffs.append(handoffs[0])
    with pytest.raises(ValueError):
        evaluate_staging_research_index_handoffs(tuple(handoffs))


def test_handoff_rejects_wrong_or_duplicate_stage_classifications() -> None:
    baseline = _handoffs()[0]
    with pytest.raises(ValueError):
        replace(baseline, classifications=baseline.classifications[:-1])
    with pytest.raises(ValueError):
        replace(
            baseline,
            classifications=(*baseline.classifications, baseline.classifications[0]),
        )


def test_unavailable_classification_remains_unavailable() -> None:
    handoffs = list(_handoffs())
    unavailable = handoffs[-1]
    handoffs[-1] = replace(
        unavailable,
        classifications=(replace(
            unavailable.classifications[0],
            outcome=StagingResearchIndexCheckOutcome.UNAVAILABLE,
        ),),
    )
    result = evaluate_staging_research_index_handoffs(tuple(handoffs))
    assert result.outcome is StagingResearchIndexAcceptanceOutcome.UNAVAILABLE
