from pathlib import Path

import pytest

from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_settings_installer as installer,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_settings_installer import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome as Outcome,
    StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable,
    install_staging_research_index_promotion_reconciliation_settings,
)


def _private(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)
    return path


def _setup(tmp_path: Path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir(mode=0o700)
    target.mkdir(mode=0o700)
    provider_target = target / "provider.env"
    process_target = target / "process.env"
    provider = _private(
        source / "provider.env",
        "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT=https://provider.test/status/\n",
    )
    process = _private(
        source / "process.env",
        "LIQUENT_STAGING_PROMOTION_RECONCILIATION_PROVIDER_SETTINGS_FILE="
        f"{provider_target}\n"
        "LIQUENT_STAGING_PROMOTION_RECONCILIATION_DATABASE_URL="
        "sqlite+pysqlite:////var/lib/liquent/staging.db\n",
    )
    return provider, provider_target, process, process_target


def test_installs_validated_pair_provider_first_and_process_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = _setup(tmp_path)
    original = installer._publish
    order = []

    def publish(directory, target, content):
        order.append(target)
        original(directory, target, content)

    monkeypatch.setattr(installer, "_publish", publish)
    assert install_staging_research_index_promotion_reconciliation_settings(*values) is Outcome.INSTALLED
    assert order == ["provider.env", "process.env"]
    assert values[1].read_bytes() == values[0].read_bytes()
    assert values[3].read_bytes() == values[2].read_bytes()
    assert values[1].stat().st_mode & 0o777 == 0o600
    assert values[3].stat().st_mode & 0o777 == 0o600


def test_existing_private_target_is_neutral_presence(tmp_path: Path) -> None:
    values = _setup(tmp_path)
    _private(values[1], "retained\n")
    assert install_staging_research_index_promotion_reconciliation_settings(*values) is Outcome.PRESENT
    assert values[1].read_text() == "retained\n"
    assert not values[3].exists()


def test_process_source_must_bind_exact_provider_target(tmp_path: Path) -> None:
    provider, provider_target, process, process_target = _setup(tmp_path)
    process.write_text(
        process.read_text().replace(str(provider_target), "/different/provider.env")
    )
    process.chmod(0o600)
    with pytest.raises(StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable):
        install_staging_research_index_promotion_reconciliation_settings(
            provider, provider_target, process, process_target
        )
    assert not provider_target.exists() and not process_target.exists()


@pytest.mark.parametrize("bad_mode", [0o644, 0o400])
def test_source_mode_fails_closed(tmp_path: Path, bad_mode: int) -> None:
    values = _setup(tmp_path)
    values[0].chmod(bad_mode)
    with pytest.raises(StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable):
        install_staging_research_index_promotion_reconciliation_settings(*values)


def test_symlink_source_and_unsafe_target_directory_fail_closed(tmp_path: Path) -> None:
    values = _setup(tmp_path)
    link = values[0].with_name("provider-link.env")
    link.symlink_to(values[0])
    with pytest.raises(StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable):
        install_staging_research_index_promotion_reconciliation_settings(
            link, values[1], values[2], values[3]
        )
    values[1].parent.chmod(0o722)
    with pytest.raises(StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable):
        install_staging_research_index_promotion_reconciliation_settings(*values)


def test_invalid_or_aliased_paths_fail_before_visibility(tmp_path: Path) -> None:
    values = _setup(tmp_path)
    for changed in (
        (Path("relative"), values[1], values[2], values[3]),
        (values[0], values[1], values[2], values[1]),
    ):
        with pytest.raises(StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable):
            install_staging_research_index_promotion_reconciliation_settings(*changed)
    assert not values[1].exists() and not values[3].exists()


def test_failure_publishing_activation_retains_inert_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = _setup(tmp_path)
    original = installer._publish

    def publish(directory, target, content):
        if target == "process.env":
            raise OSError("detail")
        original(directory, target, content)

    monkeypatch.setattr(installer, "_publish", publish)
    with pytest.raises(StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable):
        install_staging_research_index_promotion_reconciliation_settings(*values)
    assert values[1].is_file()
    assert not values[3].exists()


def test_temporary_name_collision_is_technical_unavailability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = _setup(tmp_path)
    monkeypatch.setattr(installer.secrets, "token_hex", lambda _: "fixed")
    collision = values[1].parent / ".pending-reconciliation-settings-fixed"
    _private(collision, "occupied\n")
    with pytest.raises(StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable):
        install_staging_research_index_promotion_reconciliation_settings(*values)
    assert collision.read_text() == "occupied\n"
    assert not values[1].exists() and not values[3].exists()
