"""Owner-private source for staging promotion reconciliation process settings."""

import os
from pathlib import Path
import stat

from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_settings import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessSettings,
    StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable,
)


_PREFIX = "LIQUENT_STAGING_PROMOTION_RECONCILIATION_"
_KEYS = {
    _PREFIX + "PROVIDER_SETTINGS_FILE": "provider_settings_file",
    _PREFIX + "DATABASE_URL": "database_url",
}
_MAXIMUM_BYTES = 8192


def load_staging_research_index_promotion_reconciliation_process_settings(
    path: Path,
) -> StagingResearchIndexPromotionReconciliationProcessSettings:
    descriptor = None
    try:
        if (
            not isinstance(path, Path)
            or not path.is_absolute()
            or path == Path("/")
            or ".." in path.parts
        ):
            raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > _MAXIMUM_BYTES
            or os.get_inheritable(descriptor)
        ):
            raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
        content = os.read(descriptor, _MAXIMUM_BYTES + 1)
        after = os.fstat(descriptor)
        if (
            not content
            or len(content) > _MAXIMUM_BYTES
            or (before.st_dev, before.st_ino, before.st_mode, before.st_size)
            != (after.st_dev, after.st_ino, after.st_mode, after.st_size)
            or before.st_uid != after.st_uid
            or before.st_gid != after.st_gid
            or before.st_nlink != after.st_nlink
        ):
            raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
        text = content.decode("utf-8")
        if not text.endswith("\n") or "\r" in text or "\x00" in text:
            raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
        projected = {}
        for line in text[:-1].split("\n"):
            if not line or line.count("=") != 1:
                raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
            key, value = line.split("=", 1)
            if key not in _KEYS or key in projected or not value:
                raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
            projected[key] = value
        if set(projected) != set(_KEYS):
            raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable
        return StagingResearchIndexPromotionReconciliationProcessSettings.from_mapping(
            {_KEYS[key]: value for key, value in projected.items()}
        )
    except StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except Exception:
                pass
    raise StagingResearchIndexPromotionReconciliationProcessSettingsUnavailable from None
