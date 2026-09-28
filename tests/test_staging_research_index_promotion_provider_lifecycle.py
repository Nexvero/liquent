from pathlib import Path

import httpx2
import pytest

from liquent_platform.transport import (
    staging_research_index_promotion_provider_lifecycle as lifecycle_module,
)
from liquent_platform.transport.staging_research_index_promotion_provider_lifecycle import (  # noqa: E501
    StagingResearchIndexPromotionProviderLifecycleUnavailable,
    compose_owned_staging_research_index_promotion_provider_lifecycle,
)
from tests.test_staging_research_index_promotion_reconciliation import _unknown


def write_settings(path: Path, endpoint: str = "https://provider.example/status/"):
    path.write_text(
        "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT=" + endpoint + "\n"
    )
    path.chmod(0o600)


def install_client_spy(monkeypatch: pytest.MonkeyPatch, seen_requests: list):
    created = []

    def build_client():
        client = httpx2.Client(
            transport=httpx2.MockTransport(
                lambda request: (
                    seen_requests.append(request),
                    httpx2.Response(404, content=iter(())),
                )[1]
            ),
            trust_env=False,
            follow_redirects=False,
        )
        created.append(client)
        return client

    monkeypatch.setattr(lifecycle_module, "_create_client", build_client)
    return created


def test_owned_lifecycle_uses_environment_independent_client_and_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path)
    requests = []
    created = install_client_spy(monkeypatch, requests)
    with compose_owned_staging_research_index_promotion_provider_lifecycle(path) as bundle:
        assert len(created) == 1
        assert requests == []
        assert bundle.observer.observe_committed(_unknown()) is None
        client = bundle._client
        assert not client.is_closed
    assert client.is_closed
    assert len(requests) == 1


def test_close_is_idempotent_and_closed_bundle_cannot_reenter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path)
    install_client_spy(monkeypatch, [])
    bundle = compose_owned_staging_research_index_promotion_provider_lifecycle(path)
    bundle.close()
    bundle.close()
    with pytest.raises(StagingResearchIndexPromotionProviderLifecycleUnavailable):
        bundle.__enter__()


def test_failed_composition_closes_created_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path, "http://provider.example/status/")
    created = install_client_spy(monkeypatch, [])
    with pytest.raises(StagingResearchIndexPromotionProviderLifecycleUnavailable):
        compose_owned_staging_research_index_promotion_provider_lifecycle(path)
    assert len(created) == 1 and created[0].is_closed


def test_lifecycle_exposes_no_mutation_or_retry_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path)
    install_client_spy(monkeypatch, [])
    bundle = compose_owned_staging_research_index_promotion_provider_lifecycle(path)
    try:
        assert repr(bundle) == "StagingResearchIndexPromotionProviderLifecycle()"
        for forbidden in ("promote", "retry", "claim", "credential", "reload"):
            assert not hasattr(bundle, forbidden)
    finally:
        bundle.close()


def test_client_factory_disables_ambient_environment_and_redirects() -> None:
    source = Path(lifecycle_module.__file__).read_text()
    assert "httpx2.Client(trust_env=False, follow_redirects=False)" in source
