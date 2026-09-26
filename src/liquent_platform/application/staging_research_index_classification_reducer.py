"""Closed reduction of nine response classifications to eight observations."""

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
    StagingResearchIndexObservation,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexRequestPhase,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponseClassification,
)


_SINGLE_KEYS = frozenset(
    (check, StagingResearchIndexRequestPhase.SINGLE)
    for check in StagingResearchIndexCheck
    if check is not StagingResearchIndexCheck.REVOCATION_FRESH
)
_REVOCATION_KEYS = frozenset({
    (
        StagingResearchIndexCheck.REVOCATION_FRESH,
        StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
    ),
    (
        StagingResearchIndexCheck.REVOCATION_FRESH,
        StagingResearchIndexRequestPhase.AFTER_REVOCATION,
    ),
})
_REQUIRED_KEYS = _SINGLE_KEYS | _REVOCATION_KEYS


def _revocation_outcome(
    values: tuple[StagingResearchIndexCheckOutcome, ...],
) -> StagingResearchIndexCheckOutcome:
    if any(value is StagingResearchIndexCheckOutcome.UNAVAILABLE for value in values):
        return StagingResearchIndexCheckOutcome.UNAVAILABLE
    if all(value is StagingResearchIndexCheckOutcome.PASSED for value in values):
        return StagingResearchIndexCheckOutcome.PASSED
    return StagingResearchIndexCheckOutcome.FAILED


def reduce_staging_research_index_classifications(
    classifications: tuple[StagingResearchIndexResponseClassification, ...],
) -> tuple[StagingResearchIndexObservation, ...]:
    """Require the exact phase set and return observations in canonical order."""

    if type(classifications) is not tuple or any(
        type(item) is not StagingResearchIndexResponseClassification
        or type(item.check) is not StagingResearchIndexCheck
        or type(item.phase) is not StagingResearchIndexRequestPhase
        or type(item.outcome) is not StagingResearchIndexCheckOutcome
        for item in classifications
    ):
        raise ValueError("closed response classifications are required")
    keyed = {(item.check, item.phase): item.outcome for item in classifications}
    if len(classifications) != len(_REQUIRED_KEYS) or set(keyed) != _REQUIRED_KEYS:
        raise ValueError("response classification set is incomplete or duplicated")

    observations = []
    for check in StagingResearchIndexCheck:
        if check is StagingResearchIndexCheck.REVOCATION_FRESH:
            outcome = _revocation_outcome(tuple(
                keyed[(check, phase)]
                for phase in (
                    StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
                    StagingResearchIndexRequestPhase.AFTER_REVOCATION,
                )
            ))
        else:
            outcome = keyed[(check, StagingResearchIndexRequestPhase.SINGLE)]
        observations.append(StagingResearchIndexObservation(check, outcome))
    return tuple(observations)
