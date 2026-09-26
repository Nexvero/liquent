import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_classification_reducer import (
    reduce_staging_research_index_classifications,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexRequestPhase,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponseClassification,
)


def _complete(outcome=StagingResearchIndexCheckOutcome.PASSED):
    values = []
    for check in StagingResearchIndexCheck:
        phases = (
            (
                StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
                StagingResearchIndexRequestPhase.AFTER_REVOCATION,
            )
            if check is StagingResearchIndexCheck.REVOCATION_FRESH
            else (StagingResearchIndexRequestPhase.SINGLE,)
        )
        values.extend(
            StagingResearchIndexResponseClassification(check, phase, outcome)
            for phase in phases
        )
    return tuple(values)


def test_complete_pass_set_becomes_eight_canonical_observations() -> None:
    observations = reduce_staging_research_index_classifications(_complete())
    assert tuple(item.check for item in observations) == tuple(StagingResearchIndexCheck)
    assert len(observations) == 8
    assert all(
        item.outcome is StagingResearchIndexCheckOutcome.PASSED
        for item in observations
    )


@pytest.mark.parametrize(
    ("phase", "outcome", "expected"),
    (
        (
            StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
            StagingResearchIndexCheckOutcome.FAILED,
            StagingResearchIndexCheckOutcome.FAILED,
        ),
        (
            StagingResearchIndexRequestPhase.AFTER_REVOCATION,
            StagingResearchIndexCheckOutcome.UNAVAILABLE,
            StagingResearchIndexCheckOutcome.UNAVAILABLE,
        ),
    ),
)
def test_revocation_pair_reduces_fail_closed(phase, outcome, expected) -> None:
    values = list(_complete())
    index = next(
        number for number, item in enumerate(values)
        if item.check is StagingResearchIndexCheck.REVOCATION_FRESH
        and item.phase is phase
    )
    values[index] = StagingResearchIndexResponseClassification(
        StagingResearchIndexCheck.REVOCATION_FRESH, phase, outcome
    )
    observations = reduce_staging_research_index_classifications(tuple(values))
    revocation = next(
        item for item in observations
        if item.check is StagingResearchIndexCheck.REVOCATION_FRESH
    )
    assert revocation.outcome is expected


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "wrong_phase"))
def test_non_exact_classification_sets_are_rejected(mutation) -> None:
    values = list(_complete())
    if mutation == "missing":
        values.pop()
    elif mutation == "duplicate":
        values.append(values[0])
    else:
        values[0] = StagingResearchIndexResponseClassification(
            values[0].check,
            StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
            values[0].outcome,
        )
    with pytest.raises(ValueError):
        reduce_staging_research_index_classifications(tuple(values))


def test_reducer_accepts_no_list_or_untyped_member() -> None:
    with pytest.raises(ValueError):
        reduce_staging_research_index_classifications(list(_complete()))
    with pytest.raises(ValueError):
        reduce_staging_research_index_classifications((*_complete()[:-1], object()))
