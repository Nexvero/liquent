"""No-replace installation of staging promotion reconciliation settings."""

from enum import Enum
import os
from pathlib import Path
import secrets
import stat

from liquent_platform.transport.staging_research_index_promotion_provider_settings import (
    StagingResearchIndexPromotionProviderSettings,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessSettings,
)


_PROVIDER_KEY = "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT"
_PROCESS_PROVIDER_KEY = (
    "LIQUENT_STAGING_PROMOTION_RECONCILIATION_PROVIDER_SETTINGS_FILE"
)
_PROCESS_DATABASE_KEY = "LIQUENT_STAGING_PROMOTION_RECONCILIATION_DATABASE_URL"


class StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome(Enum):
    INSTALLED = "installed"
    PRESENT = "present"


class StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable(
    Exception
):
    def __init__(self) -> None:
        super().__init__(
            "staging_research_index_promotion_reconciliation_settings_installation_unavailable"
        )


class _TargetPresent(Exception):
    pass


def install_staging_research_index_promotion_reconciliation_settings(
    provider_source: Path,
    provider_target: Path,
    process_source: Path,
    process_target: Path,
) -> StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome:
    """Install one validated provider/process settings pair without replacement."""

    try:
        paths = (provider_source, provider_target, process_source, process_target)
        if any(not _valid_path(path) for path in paths) or len(set(paths)) != 4:
            raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable

        provider_content = _read_source(provider_source, 4096)
        process_content = _read_source(process_source, 8192)
        provider_values = _projection(provider_content, {_PROVIDER_KEY})
        process_values = _projection(
            process_content, {_PROCESS_PROVIDER_KEY, _PROCESS_DATABASE_KEY}
        )
        StagingResearchIndexPromotionProviderSettings.from_mapping(
            {"endpoint": provider_values[_PROVIDER_KEY]}
        )
        process_settings = (
            StagingResearchIndexPromotionReconciliationProcessSettings.from_mapping(
                {
                    "provider_settings_file": process_values[_PROCESS_PROVIDER_KEY],
                    "database_url": process_values[_PROCESS_DATABASE_KEY],
                }
            )
        )
        if process_settings.provider_settings_file != provider_target:
            raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable

        provider_directory = _open_target_directory(provider_target.parent)
        process_directory = None
        try:
            process_directory = _open_target_directory(process_target.parent)
            if _target_state(provider_directory, provider_target.name) != "absent":
                return StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome.PRESENT
            if _target_state(process_directory, process_target.name) != "absent":
                return StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome.PRESENT
            _publish(provider_directory, provider_target.name, provider_content)
            try:
                _publish(process_directory, process_target.name, process_content)
            except _TargetPresent:
                return StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome.PRESENT
            return StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome.INSTALLED
        finally:
            if process_directory is not None:
                os.close(process_directory)
            os.close(provider_directory)
    except _TargetPresent:
        return StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome.PRESENT
    except StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable:
        raise
    except Exception:
        raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable from None


def _valid_path(path: object) -> bool:
    return (
        isinstance(path, Path)
        and path.is_absolute()
        and path != Path("/")
        and ".." not in path.parts
        and path.name not in {"", ".", ".."}
        and len(str(path)) <= 4096
    )


def _read_source(path: Path, maximum: int) -> bytes:
    descriptor = None
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or not 0 < before.st_size <= maximum
            or os.get_inheritable(descriptor)
        ):
            raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable
        content = os.read(descriptor, maximum + 1)
        after = os.fstat(descriptor)
        if (
            len(content) != before.st_size
            or (before.st_dev, before.st_ino, before.st_mode, before.st_uid,
                before.st_gid, before.st_nlink, before.st_size)
            != (after.st_dev, after.st_ino, after.st_mode, after.st_uid,
                after.st_gid, after.st_nlink, after.st_size)
        ):
            raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable
        return content
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _projection(content: bytes, keys: set[str]) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
        if not text.endswith("\n") or "\r" in text or "\x00" in text:
            raise ValueError
        values = {}
        for line in text[:-1].split("\n"):
            if not line or line.count("=") != 1:
                raise ValueError
            key, value = line.split("=", 1)
            if key not in keys or key in values or not value:
                raise ValueError
            values[key] = value
        if set(values) != keys:
            raise ValueError
        return values
    except Exception:
        raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable from None


def _open_target_directory(path: Path) -> int:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    facts = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(facts.st_mode)
        or facts.st_uid != os.geteuid()
        or stat.S_IMODE(facts.st_mode) & 0o022
        or os.get_inheritable(descriptor)
    ):
        os.close(descriptor)
        raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable
    return descriptor


def _target_state(directory: int, name: str) -> str:
    try:
        facts = os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return "absent"
    if (
        stat.S_ISREG(facts.st_mode)
        and facts.st_uid == os.geteuid()
        and stat.S_IMODE(facts.st_mode) == 0o600
        and facts.st_nlink == 1
    ):
        return "present"
    raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable


def _publish(directory: int, target: str, content: bytes) -> None:
    temporary = ".pending-reconciliation-settings-" + secrets.token_hex(16)
    descriptor = None
    created = False
    linked = False
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        created = True
        written = 0
        while written < len(content):
            count = os.write(descriptor, content[written:])
            if type(count) is not int or count < 1:
                raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable
            written += count
        facts = os.fstat(descriptor)
        if (
            not stat.S_ISREG(facts.st_mode)
            or facts.st_uid != os.geteuid()
            or stat.S_IMODE(facts.st_mode) != 0o600
            or facts.st_nlink != 1
        ):
            raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        try:
            os.link(
                temporary, target, src_dir_fd=directory, dst_dir_fd=directory,
                follow_symlinks=False,
            )
        except FileExistsError:
            raise _TargetPresent from None
        linked = True
        os.unlink(temporary, dir_fd=directory)
        created = False
        temporary = ""
        visible = os.stat(target, dir_fd=directory, follow_symlinks=False)
        if (
            not stat.S_ISREG(visible.st_mode)
            or visible.st_uid != os.geteuid()
            or stat.S_IMODE(visible.st_mode) != 0o600
            or visible.st_nlink != 1
            or visible.st_size != len(content)
        ):
            raise StagingResearchIndexPromotionReconciliationSettingsInstallationUnavailable
        os.fsync(directory)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
        if linked:
            os.fsync(directory)
