"""Trusted observation boundary for unknown staging promotion effects."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.application.staging_research_index_promotion_attempt import (
    UnknownStagingResearchIndexPromotionEffect,
)


@dataclass(frozen=True, slots=True)
class ObservedCommittedStagingResearchIndexPromotion:
    receipt: StagingResearchIndexPromotionReceipt = field(repr=False)
    observed_at: datetime

    def __post_init__(self) -> None:
        if (
            type(self.receipt) is not StagingResearchIndexPromotionReceipt
            or type(self.observed_at) is not datetime
            or self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise ValueError("committed staging promotion observation is invalid")

    def __repr__(self) -> str:
        return "ObservedCommittedStagingResearchIndexPromotion()"


class StagingResearchIndexPromotionOutcomeObserver(Protocol):
    def observe_committed(
        self, unknown: UnknownStagingResearchIndexPromotionEffect
    ) -> ObservedCommittedStagingResearchIndexPromotion | None: ...


class ReconciledStagingResearchIndexPromotionRecorder(Protocol):
    def record_reconciled_committed(
        self,
        unknown: UnknownStagingResearchIndexPromotionEffect,
        receipt: StagingResearchIndexPromotionReceipt,
        *,
        observed_at: datetime,
    ) -> StagingResearchIndexPromotionReceipt: ...


class StagingResearchIndexPromotionReconciliationUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_reconciliation_unavailable")


def reconcile_unknown_staging_research_index_promotion(
    unknown: UnknownStagingResearchIndexPromotionEffect,
    outcomes: StagingResearchIndexPromotionOutcomeObserver,
    recorder: ReconciledStagingResearchIndexPromotionRecorder,
) -> StagingResearchIndexPromotionReceipt | None:
    """Persist only a trusted, exact committed observation; otherwise stay unknown."""

    try:
        if type(unknown) is not UnknownStagingResearchIndexPromotionEffect:
            raise StagingResearchIndexPromotionReconciliationUnavailable
        observation = outcomes.observe_committed(unknown)
        if observation is None:
            return None
        if type(observation) is not ObservedCommittedStagingResearchIndexPromotion:
            raise StagingResearchIndexPromotionReconciliationUnavailable
        prepared = unknown.attempt.prepared
        receipt = observation.receipt
        if (
            receipt.operation_id != prepared.operation_id
            or receipt.actor_user_id != prepared.command.actor.user_id
            or receipt.evidence_digest != prepared.command.evidence_digest
            or receipt.candidate_digest != prepared.authority.candidate_digest
            or receipt.staging_origin != prepared.authority.staging_origin
            or receipt.target_environment != prepared.authority.target_environment
        ):
            raise StagingResearchIndexPromotionReconciliationUnavailable
        recorded = recorder.record_reconciled_committed(
            unknown, receipt, observed_at=observation.observed_at
        )
        if type(recorded) is not StagingResearchIndexPromotionReceipt or recorded != receipt:
            raise StagingResearchIndexPromotionReconciliationUnavailable
        return recorded
    except StagingResearchIndexPromotionReconciliationUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    raise StagingResearchIndexPromotionReconciliationUnavailable from None
