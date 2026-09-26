"""Registry-bound session acquisition for the controlled staging operator."""

from dataclasses import dataclass, field
from pathlib import Path

import httpx2
from sqlalchemy import Engine

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceResult,
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_controlled_session_acquisition import (
    acquire_registered_staging_research_index_session_set,
)
from liquent_platform.application.staging_research_index_fixture_control import (
    StagingResearchIndexFixtureId,
    StagingResearchIndexFixtureRevision,
)
from liquent_platform.application.staging_research_index_session_acquisition import (
    StagingResearchIndexSessionSetAcquirer,
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRevision,
)
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.persistence.staging_research_index_controlled_operator import (
    StagingResearchIndexOperatorRequest,
    run_staging_research_index_operator,
)
from liquent_platform.persistence.staging_research_index_session_set_composition import (
    compose_persistent_staging_research_index_session_set_registry,
)


class StagingResearchIndexSessionOperatorUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_session_operator_unavailable")


@dataclass(frozen=True, slots=True)
class StagingResearchIndexSessionOperatorRequest:
    run: StagingResearchIndexAcceptanceRun = field(repr=False)
    evidence_path: Path = field(repr=False)
    fixture_id: StagingResearchIndexFixtureId = field(repr=False)
    expected_active_revision: StagingResearchIndexFixtureRevision = field(repr=False)
    session_set_id: StagingResearchIndexSessionSetId = field(repr=False)
    expected_session_set_revision: StagingResearchIndexSessionSetRevision = field(
        repr=False
    )

    def __post_init__(self) -> None:
        if (
            type(self.run) is not StagingResearchIndexAcceptanceRun
            or not isinstance(self.evidence_path, Path)
            or type(self.fixture_id) is not StagingResearchIndexFixtureId
            or type(self.expected_active_revision)
            is not StagingResearchIndexFixtureRevision
            or type(self.session_set_id) is not StagingResearchIndexSessionSetId
            or type(self.expected_session_set_revision)
            is not StagingResearchIndexSessionSetRevision
        ):
            raise ValueError("exact staging session operator request is required")

    def __repr__(self) -> str:
        return "StagingResearchIndexSessionOperatorRequest()"


def run_staging_research_index_session_operator(
    engine: Engine,
    client: httpx2.Client,
    request: StagingResearchIndexSessionOperatorRequest,
    acquirer: StagingResearchIndexSessionSetAcquirer,
    *,
    material: SecureIdentityAuthorityMaterialGenerator | None = None,
) -> StagingResearchIndexAcceptanceResult | None:
    """Acquire the current registered handoff and execute exactly once."""

    if type(request) is not StagingResearchIndexSessionOperatorRequest:
        raise StagingResearchIndexSessionOperatorUnavailable
    try:
        registry = compose_persistent_staging_research_index_session_set_registry(
            engine
        )
        acquired = acquire_registered_staging_research_index_session_set(
            request.session_set_id,
            request.expected_session_set_revision,
            registry.resolver,
            acquirer,
        )
        if acquired is None:
            return None
        return run_staging_research_index_operator(
            engine,
            client,
            StagingResearchIndexOperatorRequest(
                request.run,
                request.evidence_path,
                request.fixture_id,
                request.expected_active_revision,
                acquired.handoff,
            ),
            material=material,
        )
    except StagingResearchIndexSessionOperatorUnavailable:
        raise
    except Exception:
        raise StagingResearchIndexSessionOperatorUnavailable from None
