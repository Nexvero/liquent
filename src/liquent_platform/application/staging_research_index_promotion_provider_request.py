"""Closed request boundary for one staging promotion provider-status read."""

from dataclasses import dataclass, field
import re
from typing import Protocol

from liquent_platform.adapters.staging_research_index_promotion_provider_response import (  # noqa: E501
    CommittedStagingResearchIndexPromotionProviderResponse,
    PendingStagingResearchIndexPromotionProviderResponse,
)


_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,255}\Z")


@dataclass(frozen=True, slots=True)
class StagingResearchIndexPromotionProviderStatusRequest:
    operation_id: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.operation_id) is not str or _OPAQUE.fullmatch(
            self.operation_id
        ) is None:
            raise ValueError("staging promotion provider status request is invalid")

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionProviderStatusRequest()"


class StagingResearchIndexPromotionProviderAcquisition(Protocol):
    def acquire(
        self, request: StagingResearchIndexPromotionProviderStatusRequest
    ) -> (
        PendingStagingResearchIndexPromotionProviderResponse
        | CommittedStagingResearchIndexPromotionProviderResponse
        | None
    ): ...


class StagingResearchIndexPromotionProviderRequestUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_provider_request_unavailable")


class RequestedStagingResearchIndexPromotionProviderTransport:
    __slots__ = ("_acquisition",)

    def __init__(
        self, acquisition: StagingResearchIndexPromotionProviderAcquisition
    ) -> None:
        self._acquisition = acquisition

    def read_operation(
        self, operation_id: str
    ) -> (
        PendingStagingResearchIndexPromotionProviderResponse
        | CommittedStagingResearchIndexPromotionProviderResponse
        | None
    ):
        try:
            request = StagingResearchIndexPromotionProviderStatusRequest(operation_id)
            response = self._acquisition.acquire(request)
            if response is not None and type(response) not in (
                PendingStagingResearchIndexPromotionProviderResponse,
                CommittedStagingResearchIndexPromotionProviderResponse,
            ):
                raise StagingResearchIndexPromotionProviderRequestUnavailable
            return response
        except StagingResearchIndexPromotionProviderRequestUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionProviderRequestUnavailable from None
