"""Compose the read-only staging promotion provider observer."""

import httpx2

from liquent_platform.adapters.staging_research_index_promotion_outcome import (
    TrustedStagingResearchIndexPromotionOutcomeAdapter,
)
from liquent_platform.adapters.staging_research_index_promotion_provider_response import (  # noqa: E501
    ClassifiedStagingResearchIndexPromotionStatusGateway,
)
from liquent_platform.application.staging_research_index_promotion_provider_request import (  # noqa: E501
    RequestedStagingResearchIndexPromotionProviderTransport,
)
from liquent_platform.transport.staging_research_index_promotion_provider_decoder import (  # noqa: E501
    DecodedStagingResearchIndexPromotionProviderAcquisition,
)
from liquent_platform.transport.staging_research_index_promotion_provider_http import (
    StagingResearchIndexPromotionProviderHttpAcquisition,
)


class StagingResearchIndexPromotionProviderCompositionUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_provider_composition_unavailable")


def compose_staging_research_index_promotion_provider_observer(
    client: httpx2.Client,
    endpoint: str,
) -> TrustedStagingResearchIndexPromotionOutcomeAdapter:
    """Compose one observer without owning the supplied client lifecycle."""

    try:
        raw = StagingResearchIndexPromotionProviderHttpAcquisition(client, endpoint)
        decoded = DecodedStagingResearchIndexPromotionProviderAcquisition(raw)
        requested = RequestedStagingResearchIndexPromotionProviderTransport(decoded)
        classified = ClassifiedStagingResearchIndexPromotionStatusGateway(requested)
        return TrustedStagingResearchIndexPromotionOutcomeAdapter(classified)
    except Exception:
        pass
    raise StagingResearchIndexPromotionProviderCompositionUnavailable from None
