"""Owner-private closed file source for Engine API proxy settings."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import (
    ManifestHandoffSupervisorEngineApiProxySettings,
)


_PREFIX = "LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_"
_NAMES = (
    "PROXY_SOCKET", "DAEMON_SOCKET", "CONTROL_ROOT", "SOURCE_ROOT",
    "TARGET_ROOT", "WRITER_COMMAND", "RECOVERY_COMMAND", "PROXY_UID",
    "CLIENT_GID", "DAEMON_UID", "DAEMON_GID", "HOST_OWNER_UID",
    "HOST_OWNER_GID", "DATA_OWNER_UID", "DATA_GID", "WRAPPER_UID",
    "WRAPPER_GID", "CLIENT_TIMEOUT_SECONDS", "DAEMON_TIMEOUT_SECONDS",
    "LISTENER_BACKLOG", "MAXIMUM_EXCHANGES",
)
_KEYS = frozenset(_PREFIX + name for name in _NAMES)
_MAXIMUM_BYTES = 16_384


def load_manifest_handoff_supervisor_engine_api_proxy_settings(
    path: Path,
) -> ManifestHandoffSupervisorEngineApiProxySettings:
    """Read one explicit owner-private environment projection atomically."""
    descriptor = None
    try:
        if (
            not isinstance(path, Path)
            or not path.is_absolute()
            or path == Path("/")
            or ".." in path.parts
        ):
            raise ManifestHandoffRegistryUnavailable
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
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
            raise ManifestHandoffRegistryUnavailable
        content = bytearray()
        while len(content) <= _MAXIMUM_BYTES:
            part = os.read(
                descriptor, min(4096, _MAXIMUM_BYTES + 1 - len(content))
            )
            if not part:
                break
            content.extend(part)
        after = os.fstat(descriptor)
        if (
            not content
            or len(content) > _MAXIMUM_BYTES
            or before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_mode != after.st_mode
            or before.st_uid != after.st_uid
            or before.st_gid != after.st_gid
            or before.st_nlink != after.st_nlink
            or before.st_size != after.st_size
        ):
            raise ManifestHandoffRegistryUnavailable
        return ManifestHandoffSupervisorEngineApiProxySettings.from_mapping(
            _decode(bytes(content))
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


def _decode(content: bytes) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ManifestHandoffRegistryUnavailable from None
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise ManifestHandoffRegistryUnavailable
    projected: dict[str, str] = {}
    for line in text[:-1].split("\n"):
        if not line or line.count("=") != 1:
            raise ManifestHandoffRegistryUnavailable
        key, value = line.split("=", 1)
        if key not in _KEYS or key in projected or not value:
            raise ManifestHandoffRegistryUnavailable
        projected[key] = value
    if set(projected) != _KEYS:
        raise ManifestHandoffRegistryUnavailable
    return {key[len(_PREFIX):].lower(): value for key, value in projected.items()}
