"""Detail-free outcome boundary for the readiness-gated process."""

from enum import Enum
from pathlib import Path

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_ready_process import (  # noqa: E501
    run_ready_staging_research_index_promotion_reconciliation_process,
)


class StagingResearchIndexPromotionReconciliationProcessOutcome(Enum):
    IDLE = "idle"
    RECONCILED = "reconciled"


class StagingResearchIndexPromotionReconciliationProcessOutcomeUnavailable(
    Exception
):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_process_outcome_unavailable"
        )


def observe_staging_research_index_promotion_reconciliation_process_outcome(
    process_settings_path: Path,
) -> StagingResearchIndexPromotionReconciliationProcessOutcome:
    """Run once and reveal only idle versus reconciled."""

    try:
        result = run_ready_staging_research_index_promotion_reconciliation_process(
            process_settings_path
        )
        if result is None:
            return StagingResearchIndexPromotionReconciliationProcessOutcome.IDLE
        if type(result) is StagingResearchIndexPromotionReceipt:
            return StagingResearchIndexPromotionReconciliationProcessOutcome.RECONCILED
    except Exception:
        pass
    raise StagingResearchIndexPromotionReconciliationProcessOutcomeUnavailable from None
