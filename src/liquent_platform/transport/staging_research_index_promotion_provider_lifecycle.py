"""Owned lifecycle for the settings-backed promotion provider observer."""

from pathlib import Path

import httpx2

from liquent_platform.adapters.staging_research_index_promotion_outcome import (
    TrustedStagingResearchIndexPromotionOutcomeAdapter,
)
from liquent_platform.transport.staging_research_index_promotion_provider_settings_composition import (  # noqa: E501
    compose_settings_backed_staging_research_index_promotion_provider_observer,
)


class StagingResearchIndexPromotionProviderLifecycleUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_provider_lifecycle_unavailable"
        )


class StagingResearchIndexPromotionProviderLifecycle:
    __slots__ = ("_client", "observer", "_closed")

    def __init__(
        self,
        client: httpx2.Client,
        observer: TrustedStagingResearchIndexPromotionOutcomeAdapter,
    ) -> None:
        if (
            type(client) is not httpx2.Client
            or type(observer) is not TrustedStagingResearchIndexPromotionOutcomeAdapter
        ):
            raise StagingResearchIndexPromotionProviderLifecycleUnavailable
        self._client = client
        self.observer = observer
        self._closed = False

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionProviderLifecycle()"

    def __enter__(self) -> "StagingResearchIndexPromotionProviderLifecycle":
        if self._closed:
            raise StagingResearchIndexPromotionProviderLifecycleUnavailable
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._client.close()
            except Exception:
                raise StagingResearchIndexPromotionProviderLifecycleUnavailable from None


def compose_owned_staging_research_index_promotion_provider_lifecycle(
    settings_path: Path,
) -> StagingResearchIndexPromotionProviderLifecycle:
    """Create one environment-independent client and its observer."""

    client = None
    try:
        client = _create_client()
        observer = compose_settings_backed_staging_research_index_promotion_provider_observer(
            client, settings_path
        )
        return StagingResearchIndexPromotionProviderLifecycle(client, observer)
    except Exception:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
    raise StagingResearchIndexPromotionProviderLifecycleUnavailable from None


def _create_client() -> httpx2.Client:
    return httpx2.Client(trust_env=False, follow_redirects=False)
