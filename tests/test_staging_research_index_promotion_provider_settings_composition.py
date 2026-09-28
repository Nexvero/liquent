from pathlib import Path

import httpx2
import pytest

from liquent_platform.transport.staging_research_index_promotion_provider_settings_composition import (  # noqa: E501
    StagingResearchIndexPromotionProviderSettingsCompositionUnavailable,
    compose_settings_backed_staging_research_index_promotion_provider_observer,
)
from tests.test_staging_research_index_promotion_reconciliation import _unknown


def write_settings(path: Path, endpoint: str) -> None:
    path.write_text(
        "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT=" + endpoint + "\n"
    )
    path.chmod(0o600)


def test_settings_backed_composition_loads_once_and_observes_once(
    tmp_path: Path,
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path, "https://provider.example/status/")
    seen = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(404, content=iter(()))

    client = httpx2.Client(transport=httpx2.MockTransport(handler))
    observer = compose_settings_backed_staging_research_index_promotion_provider_observer(
        client, path
    )
    path.unlink()
    assert observer.observe_committed(_unknown()) is None
    assert len(seen) == 1
    assert not client.is_closed
    client.close()


def test_composition_performs_no_request_before_observation(tmp_path: Path) -> None:
    path = tmp_path / "provider.env"
    write_settings(path, "https://provider.example/status/")
    seen = []
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda request: seen.append(request))
    )
    compose_settings_backed_staging_research_index_promotion_provider_observer(
        client, path
    )
    assert seen == []
    assert not client.is_closed
    client.close()


@pytest.mark.parametrize(
    "content",
    [
        "",
        "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT=http://provider.example/\n",
        "WRONG=https://provider.example/status/\n",
    ],
)
def test_invalid_settings_reduce_to_detail_free_composition_unavailability(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "provider.env"
    path.write_text(content)
    path.chmod(0o600)
    with pytest.raises(
        StagingResearchIndexPromotionProviderSettingsCompositionUnavailable
    ) as caught:
        compose_settings_backed_staging_research_index_promotion_provider_observer(
            httpx2.Client(), path
        )
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_composed_observer_has_no_mutation_or_retry_surface(tmp_path: Path) -> None:
    path = tmp_path / "provider.env"
    write_settings(path, "https://provider.example/status/")
    client = httpx2.Client()
    observer = compose_settings_backed_staging_research_index_promotion_provider_observer(
        client, path
    )
    for forbidden in ("promote", "retry", "claim", "credential", "reload"):
        assert not hasattr(observer, forbidden)
    assert not client.is_closed
    client.close()
