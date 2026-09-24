"""Trusted read-only adapter for committed staging promotion outcomes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.application.staging_research_index_promotion_attempt import (
    UnknownStagingResearchIndexPromotionEffect,
)
from liquent_platform.application.staging_research_index_promotion_reconciliation import (
    ObservedCommittedStagingResearchIndexPromotion,
)
from liquent_platform.identity.access import UserId


@dataclass(frozen=True, slots=True)
class TrustedCommittedStagingResearchIndexPromotionStatus:
    operation_id: str
    actor_user_id: UserId = field(repr=False)
    evidence_digest: str = field(repr=False)
    candidate_digest: str = field(repr=False)
    staging_origin: str = field(repr=False)
    target_environment: str
    observed_at: datetime


class TrustedStagingResearchIndexPromotionStatusGateway(Protocol):
    def read_committed(
        self, operation_id: str
    ) -> TrustedCommittedStagingResearchIndexPromotionStatus | None: ...


class StagingResearchIndexPromotionOutcomeAdapterUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_outcome_adapter_unavailable")


class TrustedStagingResearchIndexPromotionOutcomeAdapter:
    __slots__ = ("_gateway",)

    def __init__(self, gateway: TrustedStagingResearchIndexPromotionStatusGateway) -> None:
        self._gateway = gateway

    def __repr__(self) -> str:
        return "TrustedStagingResearchIndexPromotionOutcomeAdapter()"

    def observe_committed(
        self, unknown: UnknownStagingResearchIndexPromotionEffect
    ) -> ObservedCommittedStagingResearchIndexPromotion | None:
        try:
            if type(unknown) is not UnknownStagingResearchIndexPromotionEffect:
                raise StagingResearchIndexPromotionOutcomeAdapterUnavailable
            prepared = unknown.attempt.prepared
            status = self._gateway.read_committed(prepared.operation_id)
            if status is None:
                return None
            if type(status) is not TrustedCommittedStagingResearchIndexPromotionStatus:
                raise StagingResearchIndexPromotionOutcomeAdapterUnavailable
            receipt = StagingResearchIndexPromotionReceipt(
                status.operation_id,
                status.actor_user_id,
                status.evidence_digest,
                status.candidate_digest,
                status.staging_origin,
                status.target_environment,
            )
            expected = prepared.command
            authority = prepared.authority
            if (
                receipt.operation_id != prepared.operation_id
                or receipt.actor_user_id != expected.actor.user_id
                or receipt.evidence_digest != expected.evidence_digest
                or receipt.candidate_digest != authority.candidate_digest
                or receipt.staging_origin != authority.staging_origin
                or receipt.target_environment != authority.target_environment
            ):
                raise StagingResearchIndexPromotionOutcomeAdapterUnavailable
            return ObservedCommittedStagingResearchIndexPromotion(
                receipt, status.observed_at
            )
        except StagingResearchIndexPromotionOutcomeAdapterUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionOutcomeAdapterUnavailable from None
