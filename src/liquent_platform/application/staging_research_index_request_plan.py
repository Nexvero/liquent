"""Pure closed request plan for staging Research-index observations."""

from dataclasses import dataclass
from enum import Enum

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
)


class StagingResearchIndexCredentialSlot(str, Enum):
    NONE = "none"
    EMPTY_WORKSPACE_READER = "empty_workspace_reader"
    VISIBLE_WORKSPACE_READER = "visible_workspace_reader"
    REVOCATION_FIXTURE_READER = "revocation_fixture_reader"
    UNAVAILABLE_FIXTURE_READER = "unavailable_fixture_reader"


class StagingResearchIndexRequestPhase(str, Enum):
    SINGLE = "single"
    BEFORE_REVOCATION = "before_revocation"
    AFTER_REVOCATION = "after_revocation"


@dataclass(frozen=True, slots=True)
class StagingResearchIndexRequest:
    check: StagingResearchIndexCheck
    sequence: int
    method: str
    url: str
    credential_slot: StagingResearchIndexCredentialSlot
    phase: StagingResearchIndexRequestPhase


def plan_staging_research_index_requests(
    run: StagingResearchIndexAcceptanceRun,
) -> tuple[StagingResearchIndexRequest, ...]:
    """Return the fixed request plan without performing I/O or granting authority."""

    if type(run) is not StagingResearchIndexAcceptanceRun:
        raise ValueError("acceptance run is required")
    path = run.staging_origin + "/research"
    specifications = (
        (StagingResearchIndexCheck.ANONYMOUS_CLOSED, path,
         StagingResearchIndexCredentialSlot.NONE, StagingResearchIndexRequestPhase.SINGLE),
        (StagingResearchIndexCheck.AUTHORIZED_EMPTY, path,
         StagingResearchIndexCredentialSlot.EMPTY_WORKSPACE_READER, StagingResearchIndexRequestPhase.SINGLE),
        (StagingResearchIndexCheck.AUTHORIZED_VISIBLE, path,
         StagingResearchIndexCredentialSlot.VISIBLE_WORKSPACE_READER, StagingResearchIndexRequestPhase.SINGLE),
        (StagingResearchIndexCheck.MINIMUM_FIELDS, path,
         StagingResearchIndexCredentialSlot.VISIBLE_WORKSPACE_READER, StagingResearchIndexRequestPhase.SINGLE),
        (StagingResearchIndexCheck.SECURITY_HEADERS, path,
         StagingResearchIndexCredentialSlot.VISIBLE_WORKSPACE_READER, StagingResearchIndexRequestPhase.SINGLE),
        (StagingResearchIndexCheck.QUERY_REJECTED, path + "?workspace=probe",
         StagingResearchIndexCredentialSlot.NONE, StagingResearchIndexRequestPhase.SINGLE),
        (StagingResearchIndexCheck.REVOCATION_FRESH, path,
         StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER, StagingResearchIndexRequestPhase.BEFORE_REVOCATION),
        (StagingResearchIndexCheck.REVOCATION_FRESH, path,
         StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER, StagingResearchIndexRequestPhase.AFTER_REVOCATION),
        (StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE, path,
         StagingResearchIndexCredentialSlot.UNAVAILABLE_FIXTURE_READER, StagingResearchIndexRequestPhase.SINGLE),
    )
    return tuple(
        StagingResearchIndexRequest(check, sequence, "GET", url, credential, phase)
        for sequence, (check, url, credential, phase) in enumerate(specifications, start=1)
    )
