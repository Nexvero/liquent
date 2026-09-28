"""Compose a provider observer from one explicit settings file."""

from pathlib import Path

import httpx2

from liquent_platform.adapters.staging_research_index_promotion_outcome import (
    TrustedStagingResearchIndexPromotionOutcomeAdapter,
)
from liquent_platform.transport.staging_research_index_promotion_provider_composition import (  # noqa: E501
    compose_staging_research_index_promotion_provider_observer,
)
from liquent_platform.transport.staging_research_index_promotion_provider_settings_source import (  # noqa: E501
    load_staging_research_index_promotion_provider_settings,
)


class StagingResearchIndexPromotionProviderSettingsCompositionUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_provider_settings_composition_unavailable"
        )


def compose_settings_backed_staging_research_index_promotion_provider_observer(
    client: httpx2.Client,
    settings_path: Path,
) -> TrustedStagingResearchIndexPromotionOutcomeAdapter:
    """Load settings once and compose without owning the supplied client."""

    try:
        settings = load_staging_research_index_promotion_provider_settings(
            settings_path
        )
        return compose_staging_research_index_promotion_provider_observer(
            client, settings.endpoint
        )
    except Exception:
        pass
    raise StagingResearchIndexPromotionProviderSettingsCompositionUnavailable from None
