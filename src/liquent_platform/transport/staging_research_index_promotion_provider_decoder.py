"""Strict decoding of bounded staging promotion provider responses."""

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Protocol

from liquent_platform.adapters.staging_research_index_promotion_provider_response import (  # noqa: E501
    CommittedStagingResearchIndexPromotionProviderResponse,
    PendingStagingResearchIndexPromotionProviderResponse,
)
from liquent_platform.application.staging_research_index_promotion_provider_request import (  # noqa: E501
    StagingResearchIndexPromotionProviderStatusRequest,
)
from liquent_platform.identity.access import UserId


_MAX_BODY_BYTES = 16_384


@dataclass(frozen=True, slots=True)
class RawStagingResearchIndexPromotionProviderResponse:
    status: int
    headers: tuple[tuple[str, str], ...] = field(repr=False)
    body: bytes = field(repr=False)


class RawStagingResearchIndexPromotionProviderAcquisition(Protocol):
    def acquire_raw(
        self, request: StagingResearchIndexPromotionProviderStatusRequest
    ) -> RawStagingResearchIndexPromotionProviderResponse: ...


class StagingResearchIndexPromotionProviderDecodingUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_provider_decoding_unavailable")


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value


class DecodedStagingResearchIndexPromotionProviderAcquisition:
    __slots__ = ("_raw",)

    def __init__(self, raw: RawStagingResearchIndexPromotionProviderAcquisition) -> None:
        self._raw = raw

    def acquire(self, request: StagingResearchIndexPromotionProviderStatusRequest):
        try:
            if type(request) is not StagingResearchIndexPromotionProviderStatusRequest:
                raise StagingResearchIndexPromotionProviderDecodingUnavailable
            response = self._raw.acquire_raw(request)
            if type(response) is not RawStagingResearchIndexPromotionProviderResponse:
                raise StagingResearchIndexPromotionProviderDecodingUnavailable
            if response.status == 404 and response.body == b"":
                return None
            if len(response.body) > _MAX_BODY_BYTES:
                raise StagingResearchIndexPromotionProviderDecodingUnavailable
            headers = {name.lower(): value for name, value in response.headers}
            if headers.get("content-type") != "application/json":
                raise StagingResearchIndexPromotionProviderDecodingUnavailable
            payload = json.loads(response.body.decode("utf-8"), object_pairs_hook=_object)
            operation_id = request.operation_id
            if response.status == 202 and payload == {
                "operation_id": operation_id,
                "status": "pending",
            }:
                return PendingStagingResearchIndexPromotionProviderResponse(operation_id)
            committed = {
                "operation_id",
                "status",
                "actor_user_id",
                "evidence_digest",
                "candidate_digest",
                "staging_origin",
                "target_environment",
                "observed_at",
            }
            if response.status != 200 or set(payload) != committed:
                raise StagingResearchIndexPromotionProviderDecodingUnavailable
            if payload["operation_id"] != operation_id or payload["status"] != "committed":
                raise StagingResearchIndexPromotionProviderDecodingUnavailable
            return CommittedStagingResearchIndexPromotionProviderResponse(
                operation_id,
                UserId(payload["actor_user_id"]),
                payload["evidence_digest"],
                payload["candidate_digest"],
                payload["staging_origin"],
                payload["target_environment"],
                datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00")),
            )
        except StagingResearchIndexPromotionProviderDecodingUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionProviderDecodingUnavailable from None
