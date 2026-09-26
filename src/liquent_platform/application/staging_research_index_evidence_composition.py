"""Explicit composition of staged acquisition and evidence publication."""

from collections.abc import Mapping
from pathlib import Path

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceResult,
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot,
)
from liquent_platform.application.staging_research_index_stage_handoff import (
    StagingResearchIndexStageHandoff,
    evaluate_staging_research_index_handoffs,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    OpaqueStagingResearchSession,
    StagingResearchIndexAcquisitionStage,
    StagingResearchIndexSingleRequestAcquisition,
    acquire_staging_research_index_stage,
)
from liquent_platform.transport.staging_research_index_evidence_writer import (
    write_staging_research_index_evidence,
)


def acquire_staging_research_index_stage_handoff(
    run: StagingResearchIndexAcceptanceRun,
    stage: StagingResearchIndexAcquisitionStage,
    acquisition: StagingResearchIndexSingleRequestAcquisition,
    sessions: Mapping[
        StagingResearchIndexCredentialSlot, OpaqueStagingResearchSession
    ],
) -> StagingResearchIndexStageHandoff:
    """Acquire and immediately bind one explicitly selected stage."""

    classifications = acquire_staging_research_index_stage(
        run, stage, acquisition, sessions
    )
    return StagingResearchIndexStageHandoff(run, stage, classifications)


def publish_staging_research_index_acceptance_evidence(
    path: Path,
    handoffs: tuple[StagingResearchIndexStageHandoff, ...],
) -> StagingResearchIndexAcceptanceResult:
    """Evaluate and publish one complete handoff set without stage mutation."""

    result = evaluate_staging_research_index_handoffs(handoffs)
    write_staging_research_index_evidence(path, handoffs)
    return result
