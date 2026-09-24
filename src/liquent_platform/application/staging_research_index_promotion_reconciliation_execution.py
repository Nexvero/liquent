"""Controlled one-candidate staging promotion reconciliation execution."""

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation import (
    ReconciledStagingResearchIndexPromotionRecorder,
    StagingResearchIndexPromotionOutcomeObserver,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation_candidate import (  # noqa: E501
    StagingResearchIndexPromotionUnknownIndex,
    select_staging_research_index_promotion_reconciliation_candidate,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation_operation import (  # noqa: E501
    StagingResearchIndexPromotionUnknownResolver,
    reconcile_staging_research_index_promotion_operation,
)


class StagingResearchIndexPromotionReconciliationExecutionUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_execution_unavailable"
        )


def execute_one_staging_research_index_promotion_reconciliation(
    index: StagingResearchIndexPromotionUnknownIndex,
    unknowns: StagingResearchIndexPromotionUnknownResolver,
    outcomes: StagingResearchIndexPromotionOutcomeObserver,
    recorder: ReconciledStagingResearchIndexPromotionRecorder,
) -> StagingResearchIndexPromotionReceipt | None:
    """Select and reconcile at most one operation without retrying it."""

    try:
        operation_id = (
            select_staging_research_index_promotion_reconciliation_candidate(index)
        )
        if operation_id is None:
            return None
        result = reconcile_staging_research_index_promotion_operation(
            operation_id, unknowns, outcomes, recorder
        )
        if result is not None and type(result) is not StagingResearchIndexPromotionReceipt:
            raise StagingResearchIndexPromotionReconciliationExecutionUnavailable
        return result
    except StagingResearchIndexPromotionReconciliationExecutionUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    raise StagingResearchIndexPromotionReconciliationExecutionUnavailable from None
