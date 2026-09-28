"""Controlled callable operator for one staging Research-index acceptance run."""

from dataclasses import dataclass, field
from pathlib import Path

import httpx2
from sqlalchemy import Engine

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceResult,
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_fixture_control import (
    StagingResearchIndexFixtureId,
    StagingResearchIndexFixtureRevision,
)
from liquent_platform.application.staging_research_index_session_handoff import (
    StagingResearchIndexSessionHandoff,
)
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.persistence.staging_research_index_runtime_composition import (
    compose_staging_research_index_runtime,
)


class StagingResearchIndexOperatorUnavailable(Exception):
    code = "staging_research_index_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class StagingResearchIndexOperatorRequest:
    run: StagingResearchIndexAcceptanceRun = field(repr=False)
    evidence_path: Path = field(repr=False)
    fixture_id: StagingResearchIndexFixtureId = field(repr=False)
    expected_active_revision: StagingResearchIndexFixtureRevision = field(repr=False)
    session_handoff: StagingResearchIndexSessionHandoff = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.run) is not StagingResearchIndexAcceptanceRun
            or not isinstance(self.evidence_path, Path)
            or type(self.fixture_id) is not StagingResearchIndexFixtureId
            or type(self.expected_active_revision)
            is not StagingResearchIndexFixtureRevision
            or type(self.session_handoff) is not StagingResearchIndexSessionHandoff
        ):
            raise ValueError("exact staging Research-index operator request is required")

    def __repr__(self) -> str:
        return "StagingResearchIndexOperatorRequest()"


def run_staging_research_index_operator(
    engine: Engine,
    client: httpx2.Client,
    request: StagingResearchIndexOperatorRequest,
    *,
    material: SecureIdentityAuthorityMaterialGenerator | None = None,
) -> StagingResearchIndexAcceptanceResult:
    """Execute one explicit request without owning resources or credentials."""

    if type(request) is not StagingResearchIndexOperatorRequest:
        raise StagingResearchIndexOperatorUnavailable
    try:
        runtime = compose_staging_research_index_runtime(
            engine, client, material=material
        )
        return runtime.execute(
            run=request.run,
            evidence_path=request.evidence_path,
            fixture_id=request.fixture_id,
            expected_active_revision=request.expected_active_revision,
            session_handoff=request.session_handoff,
        )
    except StagingResearchIndexOperatorUnavailable:
        raise
    except Exception:
        raise StagingResearchIndexOperatorUnavailable from None
