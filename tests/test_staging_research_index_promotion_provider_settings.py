import pytest

from liquent_platform.transport.staging_research_index_promotion_provider_settings import (  # noqa: E501
    StagingResearchIndexPromotionProviderSettings,
    StagingResearchIndexPromotionProviderSettingsUnavailable,
)


def test_exact_endpoint_mapping_creates_hidden_settings() -> None:
    endpoint = "https://provider.example/status/"
    settings = StagingResearchIndexPromotionProviderSettings.from_mapping(
        {"endpoint": endpoint}
    )
    assert settings.endpoint == endpoint
    assert repr(settings) == "StagingResearchIndexPromotionProviderSettings()"
    assert endpoint not in repr(settings)


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"endpoint": "https://provider.example/status/", "extra": "value"},
        {"endpoint": "http://provider.example/status/"},
        {"endpoint": "https://user@provider.example/status/"},
        {"endpoint": "https://provider.example/status"},
        {"endpoint": "https://provider.example/status/?query=1"},
        {"endpoint": 42},
        None,
    ],
)
def test_missing_extra_or_malformed_settings_fail_closed(values) -> None:
    with pytest.raises(StagingResearchIndexPromotionProviderSettingsUnavailable) as caught:
        StagingResearchIndexPromotionProviderSettings.from_mapping(values)
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_settings_are_not_credentials_or_authority() -> None:
    settings = StagingResearchIndexPromotionProviderSettings.from_mapping(
        {"endpoint": "https://provider.example/status/"}
    )
    assert not hasattr(settings, "credential")
    assert not hasattr(settings, "authority")
    assert not hasattr(settings, "retry")
