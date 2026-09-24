from pathlib import Path

import pytest

from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings_source import (  # noqa: E501
    load_staging_research_index_promotion_reconciliation_process_settings,
)


_CONTENT = (
    "LIQUENT_STAGING_PROMOTION_RECONCILIATION_PROVIDER_SETTINGS_FILE="
    "/run/liquent/provider.env\n"
    "LIQUENT_STAGING_PROMOTION_RECONCILIATION_DATABASE_URL="
    "postgresql+psycopg://liquent:secret@database/liquent\n"
)


def write(path: Path, content: str = _CONTENT, mode: int = 0o600) -> None:
    path.write_text(content)
    path.chmod(mode)


def test_exact_owner_private_projection_loads_hidden_settings(tmp_path: Path) -> None:
    path = tmp_path / "reconciliation.env"
    write(path)
    settings = load_staging_research_index_promotion_reconciliation_process_settings(
        path
    )
    assert settings.provider_settings_file == Path("/run/liquent/provider.env")
    assert settings.database_url.endswith("@database/liquent")
    assert "secret" not in repr(settings)


@pytest.mark.parametrize(
    "content",
    [
        "",
        _CONTENT.rstrip("\n"),
        _CONTENT.replace("\n", "\r\n"),
        _CONTENT.split("\n", 1)[0] + "\n",
        _CONTENT + "EXTRA=value\n",
        _CONTENT.replace("DATABASE_URL", "PROVIDER_SETTINGS_FILE"),
        _CONTENT.replace("postgresql+psycopg", "mysql"),
    ],
)
def test_incomplete_duplicate_extra_or_malformed_projection_fails_closed(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "reconciliation.env"
    write(path, content)
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
    ) as caught:
        load_staging_research_index_promotion_reconciliation_process_settings(path)
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_non_private_file_and_symlink_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "reconciliation.env"
    write(path, mode=0o640)
    with pytest.raises(StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable):
        load_staging_research_index_promotion_reconciliation_process_settings(path)
    path.chmod(0o600)
    link = tmp_path / "link.env"
    link.symlink_to(path)
    with pytest.raises(StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable):
        load_staging_research_index_promotion_reconciliation_process_settings(link)


@pytest.mark.parametrize("path", [Path("relative.env"), Path("/"), None])
def test_invalid_path_fails_closed(path) -> None:
    with pytest.raises(StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable):
        load_staging_research_index_promotion_reconciliation_process_settings(path)


def test_source_has_no_environment_default_or_engine_surface() -> None:
    source = Path(
        "src/liquent_platform/transport/"
        "staging_research_index_promotion_reconciliation_process_settings_source.py"
    ).read_text()
    for forbidden in ("os.environ", "getenv", "build_engine", "create_engine"):
        assert forbidden not in source
