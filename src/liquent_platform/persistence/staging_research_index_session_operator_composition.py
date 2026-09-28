"""Provider-neutral composition for registry-bound staging-session runs."""

from dataclasses import dataclass, field

import httpx2
from sqlalchemy import Engine

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceResult,
)
from liquent_platform.application.staging_research_index_ephemeral_session_source import (
    EphemeralStagingResearchIndexSessionHandoffSource,
    StagingResearchIndexSessionHandoffResolver,
)
from liquent_platform.application.staging_research_index_session_material_acquirer import (
    InjectedStagingResearchIndexSessionSetAcquirer,
    StagingResearchIndexSessionHandoffSource,
)
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.persistence.staging_research_index_session_operator import (
    StagingResearchIndexSessionOperatorRequest,
    run_staging_research_index_session_operator,
)


@dataclass(frozen=True, slots=True)
class StagingResearchIndexSessionOperatorComposition:
    acquirer: InjectedStagingResearchIndexSessionSetAcquirer
    _engine: Engine = field(repr=False)
    _client: httpx2.Client = field(repr=False)
    _material: SecureIdentityAuthorityMaterialGenerator | None = field(repr=False)

    def __repr__(self) -> str:
        return "StagingResearchIndexSessionOperatorComposition()"

    def execute(
        self, request: StagingResearchIndexSessionOperatorRequest
    ) -> StagingResearchIndexAcceptanceResult | None:
        return run_staging_research_index_session_operator(
            self._engine,
            self._client,
            request,
            self.acquirer,
            material=self._material,
        )


def compose_staging_research_index_session_operator(
    engine: Engine,
    client: httpx2.Client,
    source: StagingResearchIndexSessionHandoffSource,
    *,
    material: SecureIdentityAuthorityMaterialGenerator | None = None,
) -> StagingResearchIndexSessionOperatorComposition:
    """Wire externally owned resources without accessing or owning them."""

    return StagingResearchIndexSessionOperatorComposition(
        acquirer=InjectedStagingResearchIndexSessionSetAcquirer(source),
        _engine=engine,
        _client=client,
        _material=material,
    )


def compose_ephemeral_staging_research_index_session_operator(
    engine: Engine,
    client: httpx2.Client,
    resolver: StagingResearchIndexSessionHandoffResolver,
    *,
    material: SecureIdentityAuthorityMaterialGenerator | None = None,
) -> StagingResearchIndexSessionOperatorComposition:
    """Bind a fresh-per-call resolver without accessing it during composition."""

    source = EphemeralStagingResearchIndexSessionHandoffSource(resolver)
    return compose_staging_research_index_session_operator(
        engine, client, source, material=material
    )
