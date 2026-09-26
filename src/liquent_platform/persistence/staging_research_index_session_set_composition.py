"""Side-effect-free composition of the persistent staging session-set registry."""

from dataclasses import dataclass

from sqlalchemy import Engine

from liquent_platform.persistence.staging_research_index_session_sets import (
    DatabaseStagingResearchIndexSessionSets,
)


@dataclass(frozen=True, slots=True)
class PersistentStagingResearchIndexSessionSetRegistry:
    resolver: DatabaseStagingResearchIndexSessionSets

    def __repr__(self) -> str:
        return "PersistentStagingResearchIndexSessionSetRegistry()"


def compose_persistent_staging_research_index_session_set_registry(
    engine: Engine,
) -> PersistentStagingResearchIndexSessionSetRegistry:
    """Bind one external engine without querying or mutating it."""

    return PersistentStagingResearchIndexSessionSetRegistry(
        resolver=DatabaseStagingResearchIndexSessionSets(engine)
    )
