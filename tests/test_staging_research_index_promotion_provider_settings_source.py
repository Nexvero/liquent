from pathlib import Path

import pytest

from liquent_platform.transport.staging_research_index_promotion_provider_settings import (  # noqa: E501
    StagingResearchIndexPromotionProviderSettingsUnavailable,
)
from liquent_platform.transport.staging_research_index_promotion_provider_settings_source import (  # noqa: E501
    load_staging_research_index_promotion_provider_settings,
)


_LINE = (
    b"LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT="
    b"https://provider.example/status/\n"
)


def write_settings(path: Path, content: bytes = _LINE, mode: int = 0o600) -> None:
    path.write_bytes(content)
    path.chmod(mode)


def test_owner_private_exact_file_loads_closed_settings(tmp_path: Path) -> None:
    path = tmp_path / "provider.env"
    write_settings(path)
    settings = load_staging_research_index_promotion_provider_settings(path)
    assert settings.endpoint == "https://provider.example/status/"
    assert "provider.example" not in repr(settings)


@pytest.mark.parametrize(
    "content",
    [
        b"",
        _LINE.rstrip(b"\n"),
        _LINE.replace(b"\n", b"\r\n"),
        b"WRONG=https://provider.example/status/\n",
        _LINE + b"EXTRA=value\n",
        b"LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT=http://provider.example/\n",
        b"\xff\n",
    ],
)
def test_malformed_projection_fails_closed(tmp_path: Path, content: bytes) -> None:
    path = tmp_path / "provider.env"
    write_settings(path, content)
    with pytest.raises(StagingResearchIndexPromotionProviderSettingsUnavailable):
        load_staging_research_index_promotion_provider_settings(path)


def test_non_private_file_and_symlink_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "provider.env"
    write_settings(path, mode=0o640)
    with pytest.raises(StagingResearchIndexPromotionProviderSettingsUnavailable):
        load_staging_research_index_promotion_provider_settings(path)
    path.chmod(0o600)
    link = tmp_path / "provider-link.env"
    link.symlink_to(path)
    with pytest.raises(StagingResearchIndexPromotionProviderSettingsUnavailable):
        load_staging_research_index_promotion_provider_settings(link)


@pytest.mark.parametrize("path", [Path("relative.env"), Path("/"), None])
def test_invalid_or_missing_path_fails_closed(path) -> None:
    with pytest.raises(StagingResearchIndexPromotionProviderSettingsUnavailable) as caught:
        load_staging_research_index_promotion_provider_settings(path)
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_source_has_no_environment_or_mutation_surface() -> None:
    source = Path(
        "src/liquent_platform/transport/"
        "staging_research_index_promotion_provider_settings_source.py"
    ).read_text()
    for forbidden in ("os.environ", "getenv", "credential", "retry", "POST", "PUT"):
        assert forbidden not in source
