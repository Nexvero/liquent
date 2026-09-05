from datetime import timedelta
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient

from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
)
from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.transport.http.app import create_app

POLICY = OidcVerificationPolicy(
    connect_timeout=timedelta(seconds=1),
    read_timeout=timedelta(seconds=2),
    total_timeout=timedelta(seconds=3),
    token_response_max_bytes=4096,
    jwks_response_max_bytes=8192,
    jwks_cache_ttl=timedelta(minutes=5),
)


def _operational() -> dict[str, object]:
    return {
        "oidc_login_lifetime": timedelta(minutes=5),
        "oidc_login_origin": "https://app.example",
        "oidc_session_lifetime": timedelta(hours=8),
        "oidc_callback_rejection": ValidatedInternalDestination("/login/rejected"),
        "oidc_callback_unavailable": ValidatedInternalDestination(
            "/login/unavailable"
        ),
    }


def test_complete_wiring_enables_both_oidc_routes_without_owning_resources(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path / 'wired.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    requests: list[httpx2.Request] = []
    client = httpx2.Client(
        transport=httpx2.MockTransport(
            lambda request: requests.append(request) or httpx2.Response(500)
        )
    )
    try:
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            database_engine=engine,
            oidc_http_client=client,
            oidc_verification_policy=POLICY,
            **_operational(),
        )
        paths = {route.path for route in app.routes}
        assert "/v1/session/oidc/login" in paths
        assert "/v1/session/oidc/callback" in paths
        assert requests == []
        with TestClient(app):
            pass
        assert client.is_closed is False
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
    finally:
        client.close()
        engine.dispose()


def test_empty_configuration_fails_login_neutrally_without_network(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path / 'empty.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    requests: list[httpx2.Request] = []
    client = httpx2.Client(
        transport=httpx2.MockTransport(
            lambda request: requests.append(request) or httpx2.Response(500)
        )
    )
    try:
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            database_engine=engine,
            oidc_http_client=client,
            oidc_verification_policy=POLICY,
            **_operational(),
        )
        with TestClient(app) as browser:
            response = browser.post(
                "/v1/session/oidc/login",
                headers={"Origin": "https://app.example"},
            )
        assert response.status_code == 503
        assert response.content == b""
        assert requests == []
    finally:
        client.close()
        engine.dispose()


@pytest.mark.parametrize(
    "supplied",
    [
        {"oidc_http_client": object()},
        {"oidc_verification_policy": POLICY},
        {"oidc_monotonic_clock": lambda: 1.0},
    ],
)
def test_partial_auto_wiring_fails_fast(tmp_path: Path, supplied: dict[str, object]) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'partial.db'}")
    try:
        with pytest.raises(ValueError, match="requires database, http client"):
            create_app(
                PlatformSettings(_secrets_dir=None),
                database_engine=engine,
                **supplied,
            )
    finally:
        engine.dispose()


def test_auto_wiring_refuses_mixed_managed_dependencies(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'mixed.db'}")
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda _: httpx2.Response(500))
    )
    try:
        with pytest.raises(ValueError, match="cannot mix"):
            create_app(
                PlatformSettings(_secrets_dir=None),
                database_engine=engine,
                oidc_http_client=client,
                oidc_verification_policy=POLICY,
                oidc_login_configurations=object(),
                **_operational(),
            )
    finally:
        client.close()
        engine.dispose()
