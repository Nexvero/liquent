from pathlib import Path
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import liquent_platform.transport.http.main as runtime
from liquent_platform.configuration import PlatformSettings
from liquent_platform.application.health import ProcessHealth
from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
)
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.transport.http.app import create_app


def _oidc(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "oidc_login_origin": "https://app.example",
        "oidc_login_lifetime_seconds": 300,
        "oidc_session_lifetime_seconds": 28_800,
        "oidc_callback_rejection": "/login/rejected",
        "oidc_callback_unavailable": "/login/unavailable",
        "oidc_connect_timeout_seconds": 5,
        "oidc_read_timeout_seconds": 10,
        "oidc_total_timeout_seconds": 15,
        "oidc_token_response_max_bytes": 65_536,
        "oidc_jwks_response_max_bytes": 262_144,
        "oidc_jwks_cache_ttl_seconds": 300,
    }
    values.update(changes)
    return values


def test_oidc_process_settings_are_all_or_none_and_summary_is_value_free() -> None:
    closed = PlatformSettings(_secrets_dir=None)
    active = PlatformSettings(_secrets_dir=None, **_oidc())

    assert closed.oidc_enabled is False
    assert active.oidc_enabled is True
    assert closed.public_summary()["oidc_enabled"] == "false"
    assert active.public_summary()["oidc_enabled"] == "true"
    assert "app.example" not in str(active.public_summary())

    with pytest.raises(ValidationError, match="must be provided together"):
        PlatformSettings(_secrets_dir=None, oidc_login_origin="https://app.example")


@pytest.mark.parametrize(
    "change",
    [
        {"oidc_connect_timeout_seconds": 16},
        {"oidc_read_timeout_seconds": 16},
        {"oidc_total_timeout_seconds": 0},
        {"oidc_token_response_max_bytes": 0},
    ],
)
def test_invalid_oidc_process_bounds_fail_before_app_build(
    change: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        PlatformSettings(_secrets_dir=None, **_oidc(**change))


class RecordingClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_entrypoint_wires_complete_oidc_and_owns_client_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'runtime.db'}"
    upgrade_to_head(url)
    client = RecordingClient()
    monkeypatch.setattr(runtime.httpx2, "Client", lambda **kwargs: client)
    settings = PlatformSettings(
        _secrets_dir=None,
        database_url=url,
        **_oidc(),
    )

    app = runtime.build_app(settings)
    paths = {route.path for route in app.routes}
    assert "/v1/session/oidc/login" in paths
    assert "/v1/session/oidc/callback" in paths
    assert client.closed is False

    with TestClient(app):
        pass
    assert client.closed is True


def test_entrypoint_closes_client_when_app_factory_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecordingClient()
    monkeypatch.setattr(runtime.httpx2, "Client", lambda **kwargs: client)
    monkeypatch.setattr(
        runtime,
        "create_app",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("factory")),
    )

    with pytest.raises(RuntimeError, match="factory"):
        runtime.build_app(PlatformSettings(_secrets_dir=None, **_oidc()))
    assert client.closed is True


def test_entrypoint_constructs_client_without_environment_inheritance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}
    client = RecordingClient()

    def construct(**kwargs):
        seen.update(kwargs)
        return client

    monkeypatch.setattr(runtime.httpx2, "Client", construct)
    monkeypatch.setattr(runtime, "create_app", lambda *args, **kwargs: object())

    runtime.build_app(PlatformSettings(_secrets_dir=None, **_oidc()))
    assert seen == {"trust_env": False, "follow_redirects": False}


def test_lifespan_closes_owned_client_even_when_shutdown_health_fails(
    tmp_path: Path,
) -> None:
    class FailingHealth(ProcessHealth):
        def mark_stopping(self) -> None:
            raise RuntimeError("stopping failed")

    url = f"sqlite:///{tmp_path / 'cleanup.db'}"
    upgrade_to_head(url)
    client = RecordingClient()
    engine = build_engine(url)
    settings = PlatformSettings(_secrets_dir=None, database_url=url)
    app = create_app(
        settings,
        health=FailingHealth(),
        database_engine=engine,
        oidc_http_client=client,
        oidc_http_client_owned=True,
        oidc_verification_policy=OidcVerificationPolicy(
            connect_timeout=timedelta(seconds=1),
            read_timeout=timedelta(seconds=1),
            total_timeout=timedelta(seconds=1),
            token_response_max_bytes=1,
            jwks_response_max_bytes=1,
            jwks_cache_ttl=timedelta(seconds=1),
        ),
        oidc_login_lifetime=timedelta(seconds=1),
        oidc_login_origin="https://app.example",
        oidc_session_lifetime=timedelta(seconds=1),
        oidc_callback_rejection=ValidatedInternalDestination("/rejected"),
        oidc_callback_unavailable=ValidatedInternalDestination("/unavailable"),
    )

    try:
        with pytest.raises(RuntimeError, match="stopping failed"):
            with TestClient(app):
                pass
        assert client.closed is True
    finally:
        engine.dispose()
