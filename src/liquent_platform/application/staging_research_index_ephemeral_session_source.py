"""Non-caching adapter for externally resolved staging-session handoffs."""

from collections.abc import Callable
from dataclasses import dataclass, field

from liquent_platform.application.staging_research_index_session_acquisition import (
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRevision,
)
from liquent_platform.application.staging_research_index_session_handoff import (
    StagingResearchIndexSessionHandoff,
)


StagingResearchIndexSessionHandoffResolver = Callable[
    [StagingResearchIndexSessionSetId, StagingResearchIndexSessionSetRevision],
    StagingResearchIndexSessionHandoff | None,
]


@dataclass(frozen=True, slots=True)
class EphemeralStagingResearchIndexSessionHandoffSource:
    """Resolve every handoff afresh without retaining returned session material."""

    _resolver: StagingResearchIndexSessionHandoffResolver = field(repr=False)

    def __repr__(self) -> str:
        return "EphemeralStagingResearchIndexSessionHandoffSource()"

    def resolve(
        self,
        session_set_id: StagingResearchIndexSessionSetId,
        expected_revision: StagingResearchIndexSessionSetRevision,
    ) -> StagingResearchIndexSessionHandoff | None:
        if (
            type(session_set_id) is not StagingResearchIndexSessionSetId
            or type(expected_revision) is not StagingResearchIndexSessionSetRevision
        ):
            raise ValueError("exact staging session-set binding is required")
        handoff = self._resolver(session_set_id, expected_revision)
        if handoff is None:
            return None
        if type(handoff) is not StagingResearchIndexSessionHandoff:
            raise ValueError("validated staging session handoff is required")
        return handoff
