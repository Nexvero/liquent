"""Classify trusted provider responses for staging promotion reconciliation."""

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Protocol

from liquent_platform.adapters.staging_research_index_promotion_outcome import (
    TrustedCommittedStagingResearchIndexPromotionStatus,
)
from liquent_platform.identity.access import UserId


_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,255}\Z")


@dataclass(frozen=True, slots=True)
class PendingStagingResearchIndexPromotionProviderResponse:
    operation_id: str

    def __post_init__(self) -> None:
        if _OPAQUE.fullmatch(self.operation_id) is None:
            raise ValueError("pending staging promotion provider response is invalid")


@dataclass(frozen=True, slots=True)
class CommittedStagingResearchIndexPromotionProviderResponse:
    operation_id: str
    actor_user_id: UserId = field(repr=False)
    evidence_digest: str = field(repr=False)
    candidate_digest: str = field(repr=False)
    staging_origin: str = field(repr=False)
    target_environment: str
    observed_at: datetime


class StagingResearchIndexPromotionProviderTransport(Protocol):
    def read_operation(
        self, operation_id: str
    ) -> (
        PendingStagingResearchIndexPromotionProviderResponse
        | CommittedStagingResearchIndexPromotionProviderResponse
        | None
    ): ...


class StagingResearchIndexPromotionProviderResponseUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_provider_response_unavailable")


class ClassifiedStagingResearchIndexPromotionStatusGateway:
    __slots__ = ("_transport",)

    def __init__(self, transport: StagingResearchIndexPromotionProviderTransport) -> None:
        self._transport = transport

    def __repr__(self) -> str:
        return "ClassifiedStagingResearchIndexPromotionStatusGateway()"

    def read_committed(
        self, operation_id: str
    ) -> TrustedCommittedStagingResearchIndexPromotionStatus | None:
        try:
            if type(operation_id) is not str or _OPAQUE.fullmatch(operation_id) is None:
                raise StagingResearchIndexPromotionProviderResponseUnavailable
            response = self._transport.read_operation(operation_id)
            if response is None:
                return None
            if type(response) is PendingStagingResearchIndexPromotionProviderResponse:
                if response.operation_id != operation_id:
                    raise StagingResearchIndexPromotionProviderResponseUnavailable
                return None
            if type(response) is not CommittedStagingResearchIndexPromotionProviderResponse:
                raise StagingResearchIndexPromotionProviderResponseUnavailable
            if response.operation_id != operation_id:
                raise StagingResearchIndexPromotionProviderResponseUnavailable
            return TrustedCommittedStagingResearchIndexPromotionStatus(
                response.operation_id,
                response.actor_user_id,
                response.evidence_digest,
                response.candidate_digest,
                response.staging_origin,
                response.target_environment,
                response.observed_at,
            )
        except StagingResearchIndexPromotionProviderResponseUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionProviderResponseUnavailable from None
