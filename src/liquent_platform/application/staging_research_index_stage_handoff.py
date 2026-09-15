"""Run-bound handoff and final evaluation of independently acquired stages."""

from dataclasses import dataclass

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceResult,
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    evaluate_staging_research_index_acceptance,
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
from liquent_platform.application.staging_research_index_staged_acquisition import (
    StagingResearchIndexAcquisitionStage,
)


_BASELINE_KEYS = frozenset({
    *(
        (check, StagingResearchIndexRequestPhase.SINGLE)
        for check in StagingResearchIndexCheck
        if check not in {
            StagingResearchIndexCheck.REVOCATION_FRESH,
            StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE,
        }
    ),
    (
        StagingResearchIndexCheck.REVOCATION_FRESH,
        StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
    ),
})
_STAGE_KEYS = {
    StagingResearchIndexAcquisitionStage.BASELINE: _BASELINE_KEYS,
    StagingResearchIndexAcquisitionStage.AFTER_REVOCATION: frozenset({(
        StagingResearchIndexCheck.REVOCATION_FRESH,
        StagingResearchIndexRequestPhase.AFTER_REVOCATION,
    )}),
    StagingResearchIndexAcquisitionStage.UNAVAILABILITY: frozenset({(
        StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE,
        StagingResearchIndexRequestPhase.SINGLE,
    )}),
}


@dataclass(frozen=True, slots=True)
class StagingResearchIndexStageHandoff:
    run: StagingResearchIndexAcceptanceRun
    stage: StagingResearchIndexAcquisitionStage
    classifications: tuple[StagingResearchIndexResponseClassification, ...]

    def __post_init__(self) -> None:
        if (
            type(self.run) is not StagingResearchIndexAcceptanceRun
            or type(self.stage) is not StagingResearchIndexAcquisitionStage
            or type(self.classifications) is not tuple
            or any(
                type(item) is not StagingResearchIndexResponseClassification
                for item in self.classifications
            )
        ):
            raise ValueError("stage handoff is invalid")
        keys = {(item.check, item.phase) for item in self.classifications}
        if (
            len(self.classifications) != len(_STAGE_KEYS[self.stage])
            or keys != _STAGE_KEYS[self.stage]
        ):
            raise ValueError("stage classifications are incomplete or duplicated")


def evaluate_staging_research_index_handoffs(
    handoffs: tuple[StagingResearchIndexStageHandoff, ...],
) -> StagingResearchIndexAcceptanceResult:
    """Evaluate exactly three same-run handoffs without cross-stage mutation."""

    if type(handoffs) is not tuple or any(
        type(item) is not StagingResearchIndexStageHandoff for item in handoffs
    ):
        raise ValueError("closed stage handoffs are required")
    by_stage = {item.stage: item for item in handoffs}
    if len(handoffs) != len(_STAGE_KEYS) or set(by_stage) != set(_STAGE_KEYS):
        raise ValueError("stage handoff set is incomplete or duplicated")
    ordered = tuple(by_stage[stage] for stage in StagingResearchIndexAcquisitionStage)
    run = ordered[0].run
    if any(item.run != run for item in ordered[1:]):
        raise ValueError("stage handoffs do not share one run binding")
    classifications = tuple(
        classification
        for handoff in ordered
        for classification in handoff.classifications
    )
    observations = reduce_staging_research_index_classifications(classifications)
    return evaluate_staging_research_index_acceptance(run, observations)
