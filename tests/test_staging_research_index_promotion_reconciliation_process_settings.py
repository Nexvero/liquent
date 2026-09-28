from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessSettings,
    StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable,
)


def values() -> dict[str, str]:
    return {
        "provider_settings_file": "/run/liquent/promotion-provider.env",
        "database_url": "postgresql+psycopg://liquent:secret@database/liquent",
    }


def test_exact_mapping_builds_hidden_immutable_process_settings() -> None:
    settings = StagingResearchIndexPromotionReconciliationProcessSettings.from_mapping(
        values()
    )
    assert settings.provider_settings_file == Path(
        "/run/liquent/promotion-provider.env"
    )
    assert settings.database_url.endswith("@database/liquent")
    assert repr(settings) == "StagingResearchIndexPromotionReconciliationProcessSettings()"
    assert "secret" not in repr(settings)
    with pytest.raises(FrozenInstanceError):
        settings.database_url = "sqlite://"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda current: current.pop("database_url"),
        lambda current: current.update(extra="value"),
        lambda current: current.update(provider_settings_file="relative.env"),
        lambda current: current.update(provider_settings_file="/run/../provider.env"),
        lambda current: current.update(database_url="mysql://database/liquent"),
        lambda current: current.update(database_url="not-a-url"),
        lambda current: current.update(database_url=42),
    ],
)
def test_incomplete_extra_or_invalid_mapping_fails_closed(mutation) -> None:
    current = values()
    mutation(current)
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
    ) as caught:
        StagingResearchIndexPromotionReconciliationProcessSettings.from_mapping(current)
    assert caught.value.__cause__ is None and caught.value.__context__ is None


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite://",
        "sqlite+pysqlite:///:memory:",
        "sqlite:////srv/liquent/runtime.db",
    ],
)
def test_supported_sqlite_forms_remain_available_for_bounded_runtimes(
    database_url: str,
) -> None:
    current = values()
    current["database_url"] = database_url
    settings = StagingResearchIndexPromotionReconciliationProcessSettings.from_mapping(
        current
    )
    assert settings.database_url == database_url


def test_settings_grant_no_authority_trigger_or_retry() -> None:
    settings = StagingResearchIndexPromotionReconciliationProcessSettings.from_mapping(
        values()
    )
    for forbidden in ("authority", "trigger", "retry", "execute", "engine"):
        assert not hasattr(settings, forbidden)
