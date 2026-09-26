"""One-shot invocation boundary for controlled staging-session acceptance."""

import httpx2
from sqlalchemy import Engine

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceResult,
)
from liquent_platform.application.staging_research_index_ephemeral_session_source import (
    StagingResearchIndexSessionHandoffResolver,
)
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.persistence.staging_research_index_session_operator import (
    StagingResearchIndexSessionOperatorRequest,
)
from liquent_platform.persistence.staging_research_index_session_operator_composition import (
    compose_ephemeral_staging_research_index_session_operator,
)


class StagingResearchIndexSessionInvocationUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_session_invocation_unavailable")


def invoke_staging_research_index_session_acceptance(
    engine: Engine,
    client: httpx2.Client,
    resolver: StagingResearchIndexSessionHandoffResolver,
    request: StagingResearchIndexSessionOperatorRequest,
    *,
    material: SecureIdentityAuthorityMaterialGenerator | None = None,
) -> StagingResearchIndexAcceptanceResult | None:
    """Compose and execute at most one exact request for this invocation."""

    if type(request) is not StagingResearchIndexSessionOperatorRequest:
        raise StagingResearchIndexSessionInvocationUnavailable
    try:
        operator = compose_ephemeral_staging_research_index_session_operator(
            engine, client, resolver, material=material
        )
        return operator.execute(request)
    except StagingResearchIndexSessionInvocationUnavailable:
        raise
    except Exception:
        raise StagingResearchIndexSessionInvocationUnavailable from None
