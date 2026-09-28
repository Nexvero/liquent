"""Non-authorizing promotion eligibility from staging acceptance."""

from dataclasses import dataclass, field

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceResult,
    StagingResearchIndexAcceptanceRun,
)


@dataclass(frozen=True, slots=True)
class StagingResearchIndexPromotionEligibility:
    """Record accepted staging evidence without granting promotion authority."""

    run: StagingResearchIndexAcceptanceRun = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.run) is not StagingResearchIndexAcceptanceRun:
            raise ValueError("exact staging acceptance run is required")

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionEligibility()"


def evaluate_staging_research_index_promotion_eligibility(
    result: StagingResearchIndexAcceptanceResult | None,
) -> StagingResearchIndexPromotionEligibility | None:
    """Return eligibility only for an exact accepted result."""

    if result is None:
        return None
    if type(result) is not StagingResearchIndexAcceptanceResult:
        raise ValueError("exact staging acceptance result is required")
    if (
        type(result.run) is not StagingResearchIndexAcceptanceRun
        or type(result.outcome) is not StagingResearchIndexAcceptanceOutcome
    ):
        raise ValueError("exact staging acceptance result is required")
    if result.outcome is not StagingResearchIndexAcceptanceOutcome.ACCEPTED:
        return None
    return StagingResearchIndexPromotionEligibility(result.run)
