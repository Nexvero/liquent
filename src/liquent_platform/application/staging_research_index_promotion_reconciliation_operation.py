"""Single-operation composition for staging promotion reconciliation."""

import re
from typing import Protocol

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.application.staging_research_index_promotion_attempt import (
    UnknownStagingResearchIndexPromotionEffect,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation import (
    ReconciledStagingResearchIndexPromotionRecorder,
    StagingResearchIndexPromotionOutcomeObserver,
    reconcile_unknown_staging_research_index_promotion,
)


_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,255}\Z")


class StagingResearchIndexPromotionUnknownResolver(Protocol):
    def resolve_unknown(
        self, operation_id: str
    ) -> UnknownStagingResearchIndexPromotionEffect | None: ...


class StagingResearchIndexPromotionReconciliationOperationUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_operation_unavailable"
        )


def reconcile_staging_research_index_promotion_operation(
    operation_id: str,
    unknowns: StagingResearchIndexPromotionUnknownResolver,
    outcomes: StagingResearchIndexPromotionOutcomeObserver,
    recorder: ReconciledStagingResearchIndexPromotionRecorder,
) -> StagingResearchIndexPromotionReceipt | None:
    """Reconcile one durable operation without scanning or retrying it."""

    try:
        if type(operation_id) is not str or _OPAQUE.fullmatch(operation_id) is None:
            raise StagingResearchIndexPromotionReconciliationOperationUnavailable
        unknown = unknowns.resolve_unknown(operation_id)
        if unknown is None:
            return None
        if (
            type(unknown) is not UnknownStagingResearchIndexPromotionEffect
            or unknown.attempt.prepared.operation_id != operation_id
        ):
            raise StagingResearchIndexPromotionReconciliationOperationUnavailable
        result = reconcile_unknown_staging_research_index_promotion(
            unknown, outcomes, recorder
        )
        if result is not None and type(result) is not StagingResearchIndexPromotionReceipt:
            raise StagingResearchIndexPromotionReconciliationOperationUnavailable
        return result
    except StagingResearchIndexPromotionReconciliationOperationUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    raise StagingResearchIndexPromotionReconciliationOperationUnavailable from None
