"""Injected acquisition of pre-provisioned opaque staging-session material."""

from dataclasses import dataclass, field
from typing import Protocol

from liquent_platform.application.staging_research_index_session_acquisition import (
    AcquiredStagingResearchIndexSessionSet,
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRevision,
)
from liquent_platform.application.staging_research_index_session_handoff import (
    StagingResearchIndexSessionHandoff,
)


class StagingResearchIndexSessionHandoffSource(Protocol):
    def resolve(
        self,
        session_set_id: StagingResearchIndexSessionSetId,
        expected_revision: StagingResearchIndexSessionSetRevision,
    ) -> StagingResearchIndexSessionHandoff | None: ...


@dataclass(frozen=True, slots=True)
class InjectedStagingResearchIndexSessionSetAcquirer:
    """Adapt one externally owned handoff source without retaining sessions."""

    _source: StagingResearchIndexSessionHandoffSource = field(repr=False)

    def __repr__(self) -> str:
        return "InjectedStagingResearchIndexSessionSetAcquirer()"

    def acquire(
        self,
        session_set_id: StagingResearchIndexSessionSetId,
        expected_revision: StagingResearchIndexSessionSetRevision,
    ) -> AcquiredStagingResearchIndexSessionSet | None:
        if (
            type(session_set_id) is not StagingResearchIndexSessionSetId
            or type(expected_revision) is not StagingResearchIndexSessionSetRevision
        ):
            raise ValueError("exact staging session-set binding is required")
        handoff = self._source.resolve(session_set_id, expected_revision)
        if handoff is None:
            return None
        if type(handoff) is not StagingResearchIndexSessionHandoff:
            raise ValueError("validated staging session handoff is required")
        return AcquiredStagingResearchIndexSessionSet(
            session_set_id, expected_revision, handoff
        )
