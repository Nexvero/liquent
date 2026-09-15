"""Registry-bound controlled acquisition of one staging session set."""

from liquent_platform.application.staging_research_index_session_acquisition import (
    AcquiredStagingResearchIndexSessionSet,
    StagingResearchIndexSessionSetAcquirer,
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRegistry,
    StagingResearchIndexSessionSetRevision,
    validate_staging_research_index_session_set_acquisition,
)


class StagingResearchIndexControlledSessionAcquisitionUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_controlled_session_acquisition_unavailable")


def acquire_registered_staging_research_index_session_set(
    session_set_id: StagingResearchIndexSessionSetId,
    expected_revision: StagingResearchIndexSessionSetRevision,
    registry: StagingResearchIndexSessionSetRegistry,
    acquirer: StagingResearchIndexSessionSetAcquirer,
) -> AcquiredStagingResearchIndexSessionSet | None:
    """Acquire only while the exact registry binding remains current."""

    try:
        if (
            type(session_set_id) is not StagingResearchIndexSessionSetId
            or type(expected_revision) is not StagingResearchIndexSessionSetRevision
        ):
            raise StagingResearchIndexControlledSessionAcquisitionUnavailable
        before = registry.resolve(session_set_id, expected_revision)
        if before is None:
            return None
        acquired = acquirer.acquire(session_set_id, expected_revision)
        if acquired is None:
            return None
        validate_staging_research_index_session_set_acquisition(
            session_set_id, expected_revision, acquired
        )
        after = registry.resolve(session_set_id, expected_revision)
        if after is None or after != before:
            return None
        return acquired
    except StagingResearchIndexControlledSessionAcquisitionUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    raise StagingResearchIndexControlledSessionAcquisitionUnavailable from None
