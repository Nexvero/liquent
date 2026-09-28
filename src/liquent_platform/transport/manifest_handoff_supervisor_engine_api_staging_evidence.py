"""Closed offline evidence artifact for joint Engine API staging."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable

_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ENVIRONMENT = re.compile(r"[a-z][a-z0-9-]{0,62}\Z")
_KEYS = ("schema_version", "environment_id", "observed_at", "image_digest", "render_sha256", "inspect_sha256", "health_sha256", "policy_sha256", "shutdown_sha256")

@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiStagingEvidence:
    schema_version: int
    environment_id: str
    observed_at: str
    image_digest: str
    render_sha256: str
    inspect_sha256: str
    health_sha256: str
    policy_sha256: str
    shutdown_sha256: str

    def __post_init__(self):
        hashes = (self.render_sha256, self.inspect_sha256, self.health_sha256, self.policy_sha256, self.shutdown_sha256)
        try:
            parsed = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        if (self.schema_version != 1 or type(self.schema_version) is not int
                or type(self.environment_id) is not str or not _ENVIRONMENT.fullmatch(self.environment_id)
                or type(self.observed_at) is not str or not self.observed_at.endswith("Z")
                or parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0
                or type(self.image_digest) is not str or not _DIGEST.fullmatch(self.image_digest)
                or any(type(value) is not str or not _HASH.fullmatch(value) for value in hashes)
                or len(set(hashes)) != len(hashes)):
            raise ManifestHandoffRegistryUnavailable

    def __repr__(self): return "ManifestHandoffSupervisorEngineApiStagingEvidence()"

def encode_manifest_handoff_supervisor_engine_api_staging_evidence(value):
    if type(value) is not ManifestHandoffSupervisorEngineApiStagingEvidence: raise ManifestHandoffRegistryUnavailable
    payload = {key: getattr(value, key) for key in _KEYS}
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")

def decode_manifest_handoff_supervisor_engine_api_staging_evidence(content: bytes):
    try:
        if type(content) is not bytes or not content.endswith(b"\n") or len(content) > 4096: raise ManifestHandoffRegistryUnavailable
        payload = json.loads(content)
        if type(payload) is not dict or set(payload) != set(_KEYS): raise ManifestHandoffRegistryUnavailable
        value = ManifestHandoffSupervisorEngineApiStagingEvidence(**payload)
        if encode_manifest_handoff_supervisor_engine_api_staging_evidence(value) != content: raise ManifestHandoffRegistryUnavailable
        return value
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None

def write_manifest_handoff_supervisor_engine_api_staging_evidence(path: Path, value) -> None:
    descriptor = None
    try:
        if not isinstance(path, Path) or not path.is_absolute() or path == Path("/") or ".." in path.parts: raise ManifestHandoffRegistryUnavailable
        content = encode_manifest_handoff_supervisor_engine_api_staging_evidence(value)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        written = 0
        while written < len(content):
            count = os.write(descriptor, content[written:])
            if type(count) is not int or count < 1: raise ManifestHandoffRegistryUnavailable
            written += count
        os.fsync(descriptor)
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass
