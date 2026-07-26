from pathlib import Path

import pytest
from pydantic import ValidationError

from liquent_platform.configuration import Environment, PlatformSettings


def test_safe_local_defaults() -> None:
    settings = PlatformSettings(_secrets_dir=None)
    assert settings.environment is Environment.LOCAL
    assert settings.http_host == "127.0.0.1"
    assert settings.job_concurrency == 1
    assert settings.trading_connectivity == "disabled"
    assert settings.database_url is None
    assert settings.research_data_root is None
    assert settings.public_summary()["research_start_enabled"] == "false"


def test_environment_values_use_liquent_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIQUENT_HTTP_PORT", "8123")
    monkeypatch.setenv("LIQUENT_LOG_LEVEL", "WARNING")
    settings = PlatformSettings(_secrets_dir=None)
    assert settings.http_port == 8123
    assert settings.log_level.value == "WARNING"


def test_research_data_root_is_explicit_and_path_is_not_logged(tmp_path: Path) -> None:
    settings = PlatformSettings(_secrets_dir=None, research_data_root=tmp_path)

    assert settings.research_data_root == tmp_path
    assert settings.public_summary()["research_start_enabled"] == "true"
    assert str(tmp_path) not in str(settings.public_summary())


@pytest.mark.parametrize("environment", ("preview", "production"))
def test_research_start_is_rejected_without_authentication_in_shared_environments(
    environment: str, tmp_path: Path
) -> None:
    values: dict[str, object] = {
        "environment": environment,
        "research_data_root": tmp_path,
    }
    if environment == "production":
        values.update(
            log_format="json",
            http_host="0.0.0.0",
            database_url="postgresql+psycopg://liquent:test@postgres/liquent",
        )

    with pytest.raises(ValidationError, match="limited to local and ci"):
        PlatformSettings(_secrets_dir=None, **values)


def test_ci_may_enable_controlled_local_research(tmp_path: Path) -> None:
    settings = PlatformSettings(
        _secrets_dir=None,
        environment="ci",
        research_data_root=tmp_path,
    )

    assert settings.research_data_root == tmp_path


@pytest.mark.parametrize(
    ("field", "value"),
    (("job_concurrency", 2), ("trading_connectivity", "enabled"), ("http_port", 70000)),
)
def test_unsafe_or_invalid_values_fail(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        PlatformSettings(_secrets_dir=None, **{field: value})


def test_production_requires_json_wildcard_listener_and_database_secret() -> None:
    with pytest.raises(ValidationError, match="LIQUENT_LOG_FORMAT=json"):
        PlatformSettings(_secrets_dir=None, environment="production")
    with pytest.raises(ValidationError, match="LIQUENT_HTTP_HOST=0.0.0.0"):
        PlatformSettings(
            _secrets_dir=None,
            environment="production",
            log_format="json",
        )
    with pytest.raises(ValidationError, match="database_url secret file"):
        PlatformSettings(
            _secrets_dir=None,
            environment="production",
            log_format="json",
            http_host="0.0.0.0",
        )


def test_secret_file_is_loaded_and_never_exposed_in_public_summary(tmp_path: Path) -> None:
    secret = "postgresql+psycopg://liquent:sensitive@postgres/liquent"
    (tmp_path / "database_url").write_text(secret, encoding="utf-8")
    settings = PlatformSettings(
        _secrets_dir=tmp_path,
        environment="production",
        log_format="json",
        http_host="0.0.0.0",
    )
    assert settings.database_url is not None
    assert settings.database_url.get_secret_value() == secret
    assert "database_url" not in settings.public_summary()
    assert "sensitive" not in str(settings.public_summary())


def test_production_rejects_an_unapproved_database_driver() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+psycopg"):
        PlatformSettings(
            _secrets_dir=None,
            environment="production",
            log_format="json",
            http_host="0.0.0.0",
            database_url="postgresql://liquent:secret@postgres/liquent",
        )
