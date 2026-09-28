"""Owner-private source for Engine API health run settings."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_run_settings import ManifestHandoffSupervisorEngineApiHealthRunSettings


_KEY = "LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_HEALTH_MAXIMUM_EXCHANGES"
_MAXIMUM_BYTES = 256


def load_manifest_handoff_supervisor_engine_api_health_run_settings(
    path: Path,
) -> ManifestHandoffSupervisorEngineApiHealthRunSettings:
    descriptor = None
    try:
        if (not isinstance(path, Path) or not path.is_absolute()
                or path == Path("/") or ".." in path.parts):
            raise ManifestHandoffRegistryUnavailable
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid()
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
                or before.st_size < 1 or before.st_size > _MAXIMUM_BYTES
                or os.get_inheritable(descriptor)):
            raise ManifestHandoffRegistryUnavailable
        content = bytearray()
        while len(content) <= _MAXIMUM_BYTES:
            part = os.read(descriptor, _MAXIMUM_BYTES + 1 - len(content))
            if not part:
                break
            content.extend(part)
        after = os.fstat(descriptor)
        if (not content or len(content) > _MAXIMUM_BYTES
                or (before.st_dev, before.st_ino, before.st_mode, before.st_uid,
                    before.st_gid, before.st_nlink, before.st_size) !=
                   (after.st_dev, after.st_ino, after.st_mode, after.st_uid,
                    after.st_gid, after.st_nlink, after.st_size)):
            raise ManifestHandoffRegistryUnavailable
        text = bytes(content).decode("utf-8")
        if not text.endswith("\n") or "\r" in text or "\x00" in text:
            raise ManifestHandoffRegistryUnavailable
        line = text[:-1]
        if line.count("=") != 1:
            raise ManifestHandoffRegistryUnavailable
        key, value = line.split("=", 1)
        if key != _KEY or not value:
            raise ManifestHandoffRegistryUnavailable
        return ManifestHandoffSupervisorEngineApiHealthRunSettings.from_mapping(
            {"maximum_exchanges": value}
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except Exception:
                pass
