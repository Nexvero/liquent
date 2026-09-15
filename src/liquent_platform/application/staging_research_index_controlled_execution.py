"""Controlled staging Research-index acquisition with mandatory restoration."""

from collections.abc import Mapping
from pathlib import Path

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceResult,
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_evidence_composition import (
    acquire_staging_research_index_stage_handoff,
    publish_staging_research_index_acceptance_evidence,
)
from liquent_platform.application.staging_research_index_fixture_control import (
    StagingResearchIndexFixtureId,
    StagingResearchIndexFixtureRestorer,
    StagingResearchIndexFixtureRevoker,
    StagingResearchIndexFixtureRevision,
    validate_staging_research_index_fixture_restoration,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    OpaqueStagingResearchSession,
    StagingResearchIndexAcquisitionStage,
    StagingResearchIndexSingleRequestAcquisition,
)


class StagingResearchIndexControlledExecutionUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_controlled_execution_unavailable")


def execute_controlled_staging_research_index_acceptance(
    *,
    run: StagingResearchIndexAcceptanceRun,
    evidence_path: Path,
    fixture_id: StagingResearchIndexFixtureId,
    expected_active_revision: StagingResearchIndexFixtureRevision,
    revoker: StagingResearchIndexFixtureRevoker,
    restorer: StagingResearchIndexFixtureRestorer,
    acquisition: StagingResearchIndexSingleRequestAcquisition,
    sessions: Mapping[
        StagingResearchIndexAcquisitionStage,
        dict[StagingResearchIndexCredentialSlot, OpaqueStagingResearchSession],
    ],
) -> StagingResearchIndexAcceptanceResult:
    """Run the three stages while restoring before evidence publication."""

    try:
        if type(sessions) is not dict or set(sessions) != set(
            StagingResearchIndexAcquisitionStage
        ):
            raise StagingResearchIndexControlledExecutionUnavailable
        baseline = acquire_staging_research_index_stage_handoff(
            run,
            StagingResearchIndexAcquisitionStage.BASELINE,
            acquisition,
            sessions[StagingResearchIndexAcquisitionStage.BASELINE],
        )
        revoked = revoker.revoke(fixture_id, expected_active_revision)
        try:
            after_revocation = acquire_staging_research_index_stage_handoff(
                run,
                StagingResearchIndexAcquisitionStage.AFTER_REVOCATION,
                acquisition,
                sessions[StagingResearchIndexAcquisitionStage.AFTER_REVOCATION],
            )
        finally:
            restored = restorer.restore(revoked)
            validate_staging_research_index_fixture_restoration(revoked, restored)
        unavailability = acquire_staging_research_index_stage_handoff(
            run,
            StagingResearchIndexAcquisitionStage.UNAVAILABILITY,
            acquisition,
            sessions[StagingResearchIndexAcquisitionStage.UNAVAILABILITY],
        )
        return publish_staging_research_index_acceptance_evidence(
            evidence_path, (baseline, after_revocation, unavailability)
        )
    except StagingResearchIndexControlledExecutionUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    raise StagingResearchIndexControlledExecutionUnavailable
