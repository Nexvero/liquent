"""Offline composition of the staging Research-index acceptance pipeline."""

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceResult,
    StagingResearchIndexAcceptanceRun,
    evaluate_staging_research_index_acceptance,
)
from liquent_platform.application.staging_research_index_classification_reducer import (
    reduce_staging_research_index_classifications,
)
from liquent_platform.application.staging_research_index_request_plan import (
    plan_staging_research_index_requests,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponse,
    classify_staging_research_index_response,
)


def evaluate_staging_research_index_responses(
    run: StagingResearchIndexAcceptanceRun,
    responses: tuple[StagingResearchIndexResponse, ...],
) -> StagingResearchIndexAcceptanceResult:
    """Evaluate one exact offline response set without performing acquisition."""

    requests = plan_staging_research_index_requests(run)
    if type(responses) is not tuple or len(responses) != len(requests):
        raise ValueError("exact offline response set is required")
    classifications = tuple(
        classify_staging_research_index_response(request, response)
        for request, response in zip(requests, responses, strict=True)
    )
    observations = reduce_staging_research_index_classifications(classifications)
    return evaluate_staging_research_index_acceptance(run, observations)
