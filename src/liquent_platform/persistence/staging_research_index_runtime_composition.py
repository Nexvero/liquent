"""Runtime composition for explicitly controlled staging Research-index runs."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import httpx2
from sqlalchemy import Engine

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceResult,
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_controlled_execution import (
    execute_controlled_staging_research_index_acceptance,
)
from liquent_platform.application.staging_research_index_fixture_control import (
    StagingResearchIndexFixtureId,
    StagingResearchIndexFixtureRevision,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    OpaqueStagingResearchSession,
    StagingResearchIndexAcquisitionStage,
)
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.persistence.staging_research_index_control_composition import (
    PersistentStagingResearchIndexFixtureControl,
    compose_persistent_staging_research_index_fixture_control,
)
from liquent_platform.transport.staging_research_index_http_acquisition import (
    StagingResearchIndexHttpAcquisition,
)


@dataclass(frozen=True, slots=True)
class StagingResearchIndexRuntimeComposition:
    fixture_control: PersistentStagingResearchIndexFixtureControl
    acquisition: StagingResearchIndexHttpAcquisition
    _client: httpx2.Client = field(repr=False)

    def __repr__(self) -> str:
        return "StagingResearchIndexRuntimeComposition()"

    def execute(
        self,
        *,
        run: StagingResearchIndexAcceptanceRun,
        evidence_path: Path,
        fixture_id: StagingResearchIndexFixtureId,
        expected_active_revision: StagingResearchIndexFixtureRevision,
        sessions: Mapping[
            StagingResearchIndexAcquisitionStage,
            dict[
                StagingResearchIndexCredentialSlot,
                OpaqueStagingResearchSession,
            ],
        ],
    ) -> StagingResearchIndexAcceptanceResult:
        return execute_controlled_staging_research_index_acceptance(
            run=run,
            evidence_path=evidence_path,
            fixture_id=fixture_id,
            expected_active_revision=expected_active_revision,
            revoker=self.fixture_control.controller,
            restorer=self.fixture_control.controller,
            acquisition=self.acquisition,
            sessions=sessions,
        )


def compose_staging_research_index_runtime(
    engine: Engine,
    client: httpx2.Client,
    *,
    material: SecureIdentityAuthorityMaterialGenerator | None = None,
) -> StagingResearchIndexRuntimeComposition:
    """Wire explicit execution without database or network activity."""

    return StagingResearchIndexRuntimeComposition(
        fixture_control=compose_persistent_staging_research_index_fixture_control(
            engine, material=material
        ),
        acquisition=StagingResearchIndexHttpAcquisition(client),
        _client=client,
    )
