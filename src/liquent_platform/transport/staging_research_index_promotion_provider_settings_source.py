"""Owner-private file source for promotion provider endpoint settings."""

import os
from pathlib import Path
import stat

from liquent_platform.transport.staging_research_index_promotion_provider_settings import (  # noqa: E501
    StagingResearchIndexPromotionProviderSettings,
    StagingResearchIndexPromotionProviderSettingsUnavailable,
)


_KEY = "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT"
_MAXIMUM_BYTES = 4096


def load_staging_research_index_promotion_provider_settings(
    path: Path,
) -> StagingResearchIndexPromotionProviderSettings:
    """Read one explicit, owner-private settings projection."""

    descriptor = None
    try:
        if (
            not isinstance(path, Path)
            or not path.is_absolute()
            or path == Path("/")
            or ".." in path.parts
        ):
            raise StagingResearchIndexPromotionProviderSettingsUnavailable
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
            raise StagingResearchIndexPromotionProviderSettingsUnavailable
        content = os.read(descriptor, _MAXIMUM_BYTES + 1)
        after = os.fstat(descriptor)
        if (
            not content
            or len(content) > _MAXIMUM_BYTES
            or (before.st_dev, before.st_ino, before.st_mode, before.st_uid)
            != (after.st_dev, after.st_ino, after.st_mode, after.st_uid)
            or before.st_gid != after.st_gid
            or before.st_nlink != after.st_nlink
            or before.st_size != after.st_size
        ):
            raise StagingResearchIndexPromotionProviderSettingsUnavailable
        text = content.decode("utf-8")
        if not text.endswith("\n") or "\r" in text or "\x00" in text:
            raise StagingResearchIndexPromotionProviderSettingsUnavailable
        lines = text[:-1].split("\n")
        if len(lines) != 1 or lines[0].count("=") != 1:
            raise StagingResearchIndexPromotionProviderSettingsUnavailable
        key, endpoint = lines[0].split("=", 1)
        if key != _KEY or not endpoint:
            raise StagingResearchIndexPromotionProviderSettingsUnavailable
        return StagingResearchIndexPromotionProviderSettings.from_mapping(
            {"endpoint": endpoint}
        )
    except StagingResearchIndexPromotionProviderSettingsUnavailable:
        raise
    except Exception:
        raise StagingResearchIndexPromotionProviderSettingsUnavailable from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except Exception:
                pass
