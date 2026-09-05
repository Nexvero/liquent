"""Closed owner-private settings for the joint Engine API runtime."""
from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import stat
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable

_PREFIX = "LIQUENT_MANIFEST_HANDOFF_SUPERVISOR_ENGINE_API_JOINT_"
_NAMES = ("PROXY_SETTINGS_FILE", "HEALTH_AUTHORITY_FILE", "HEALTH_RUN_SETTINGS_FILE", "POLL_TIMEOUT_MILLISECONDS", "JOIN_TIMEOUT_MILLISECONDS")

@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiJointSettings:
    proxy_settings_file: Path
    health_authority_file: Path
    health_run_settings_file: Path
    poll_timeout_seconds: float
    join_timeout_seconds: float

    @classmethod
    def from_mapping(cls, values: dict[str, str]):
        try:
            if type(values) is not dict or set(values) != {name.lower() for name in _NAMES}:
                raise ManifestHandoffRegistryUnavailable
            paths = {name: Path(values[name]) for name in ("proxy_settings_file", "health_authority_file", "health_run_settings_file")}
            if len(set(paths.values())) != 3 or any(not path.is_absolute() or path == Path("/") or ".." in path.parts or str(path) != values[name] for name, path in paths.items()):
                raise ManifestHandoffRegistryUnavailable
            numbers = []
            for name in ("poll_timeout_milliseconds", "join_timeout_milliseconds"):
                raw = values[name]
                if type(raw) is not str or not raw.isascii() or not raw.isdigit() or (len(raw) > 1 and raw[0] == "0"):
                    raise ManifestHandoffRegistryUnavailable
                numbers.append(int(raw))
            if not (10 <= numbers[0] <= 60_000 and numbers[0] <= numbers[1] <= 300_000):
                raise ManifestHandoffRegistryUnavailable
            return cls(**paths, poll_timeout_seconds=numbers[0] / 1000, join_timeout_seconds=numbers[1] / 1000)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def __repr__(self): return "ManifestHandoffSupervisorEngineApiJointSettings()"

def load_manifest_handoff_supervisor_engine_api_joint_settings(path: Path):
    descriptor = None
    try:
        if not isinstance(path, Path) or not path.is_absolute() or path == Path("/") or ".." in path.parts: raise ManifestHandoffRegistryUnavailable
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid() or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1 or before.st_size < 1 or before.st_size > 4096 or os.get_inheritable(descriptor): raise ManifestHandoffRegistryUnavailable
        content = os.read(descriptor, 4097); after = os.fstat(descriptor)
        if not content or len(content) > 4096 or (before.st_dev, before.st_ino, before.st_size, before.st_mode) != (after.st_dev, after.st_ino, after.st_size, after.st_mode): raise ManifestHandoffRegistryUnavailable
        text = content.decode("utf-8")
        if not text.endswith("\n") or "\r" in text or "\x00" in text: raise ManifestHandoffRegistryUnavailable
        projected = {}
        allowed = {_PREFIX + name for name in _NAMES}
        for line in text[:-1].split("\n"):
            if line.count("=") != 1: raise ManifestHandoffRegistryUnavailable
            key, value = line.split("=", 1)
            if key not in allowed or key in projected or not value: raise ManifestHandoffRegistryUnavailable
            projected[key] = value
        if set(projected) != allowed: raise ManifestHandoffRegistryUnavailable
        return ManifestHandoffSupervisorEngineApiJointSettings.from_mapping({key[len(_PREFIX):].lower(): value for key, value in projected.items()})
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass
