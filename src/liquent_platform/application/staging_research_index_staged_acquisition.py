"""Closed staged acquisition and immediate response classification."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Protocol

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot,
    StagingResearchIndexRequest,
    StagingResearchIndexRequestPhase,
    plan_staging_research_index_requests,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponse,
    StagingResearchIndexResponseClassification,
    classify_staging_research_index_response,
)


_SESSION = re.compile(r"[A-Za-z0-9._~-]{16,4096}\Z")


@dataclass(frozen=True, slots=True)
class OpaqueStagingResearchSession:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str or _SESSION.fullmatch(self.value) is None:
            raise ValueError("opaque staging session is invalid")


class StagingResearchIndexAcquisitionStage(str, Enum):
    BASELINE = "baseline"
    AFTER_REVOCATION = "after_revocation"
    UNAVAILABILITY = "unavailability"


class StagingResearchIndexSingleRequestAcquisition(Protocol):
    def acquire(
        self,
        request: StagingResearchIndexRequest,
        session: OpaqueStagingResearchSession | None,
    ) -> StagingResearchIndexResponse: ...


def _stage_requests(
    run: StagingResearchIndexAcceptanceRun,
    stage: StagingResearchIndexAcquisitionStage,
) -> tuple[StagingResearchIndexRequest, ...]:
    plan = plan_staging_research_index_requests(run)
    if stage is StagingResearchIndexAcquisitionStage.BASELINE:
        return tuple(
            request for request in plan
            if request.check is not StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE
            and request.phase is not StagingResearchIndexRequestPhase.AFTER_REVOCATION
        )
    if stage is StagingResearchIndexAcquisitionStage.AFTER_REVOCATION:
        return tuple(
            request for request in plan
            if request.phase is StagingResearchIndexRequestPhase.AFTER_REVOCATION
        )
    return tuple(
        request for request in plan
        if request.check is StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE
    )


def acquire_staging_research_index_stage(
    run: StagingResearchIndexAcceptanceRun,
    stage: StagingResearchIndexAcquisitionStage,
    acquisition: StagingResearchIndexSingleRequestAcquisition,
    sessions: Mapping[
        StagingResearchIndexCredentialSlot, OpaqueStagingResearchSession
    ],
) -> tuple[StagingResearchIndexResponseClassification, ...]:
    """Acquire one closed stage without performing authority mutation."""

    if type(stage) is not StagingResearchIndexAcquisitionStage:
        raise ValueError("closed acquisition stage is required")
    requests = _stage_requests(run, stage)
    required_slots = {
        request.credential_slot for request in requests
        if request.credential_slot is not StagingResearchIndexCredentialSlot.NONE
    }
    if type(sessions) is not dict or set(sessions) != required_slots or any(
        type(value) is not OpaqueStagingResearchSession
        for value in sessions.values()
    ):
        raise ValueError("exact stage sessions are required")

    classifications = []
    for request in requests:
        session = sessions.get(request.credential_slot)
        try:
            response = acquisition.acquire(request, session)
            classification = classify_staging_research_index_response(
                request, response
            )
        except Exception:
            classification = StagingResearchIndexResponseClassification(
                request.check,
                request.phase,
                StagingResearchIndexCheckOutcome.UNAVAILABLE,
            )
        classifications.append(classification)
    return tuple(classifications)
