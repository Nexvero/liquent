"""Read-only content and freshness verifier for private staging evidence."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import stat
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_evidence import decode_manifest_handoff_supervisor_engine_api_staging_evidence

_MAX_ARTIFACT_BYTES = 16 * 1024 * 1024

def _read(path: Path, maximum: int) -> bytes:
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        facts = os.fstat(descriptor)
        if (not stat.S_ISREG(facts.st_mode) or facts.st_uid != os.geteuid()
                or stat.S_IMODE(facts.st_mode) != 0o600 or facts.st_nlink != 1
                or facts.st_size < 1 or facts.st_size > maximum or os.get_inheritable(descriptor)):
            raise ManifestHandoffRegistryUnavailable
        content = bytearray()
        while len(content) <= maximum:
            part = os.read(descriptor, min(65536, maximum + 1 - len(content)))
            if not part: break
            content.extend(part)
        after = os.fstat(descriptor)
        if len(content) != facts.st_size or (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_nlink) != (after.st_dev, after.st_ino, after.st_mode, after.st_nlink):
            raise ManifestHandoffRegistryUnavailable
        return bytes(content)
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass

def verify(evidence_file: Path, render_file: Path, inspect_file: Path,
           health_file: Path, policy_file: Path, shutdown_file: Path, *,
           expected_environment: str, maximum_age_seconds: int,
           now: datetime | None = None) -> None:
    try:
        paths = (evidence_file, render_file, inspect_file, health_file, policy_file, shutdown_file)
        if (len(set(paths)) != 6 or any(not isinstance(path, Path) or not path.is_absolute() or path == Path("/") or ".." in path.parts for path in paths)
                or type(expected_environment) is not str or not expected_environment
                or type(maximum_age_seconds) is not int or maximum_age_seconds < 1 or maximum_age_seconds > 604800):
            raise ManifestHandoffRegistryUnavailable
        evidence = decode_manifest_handoff_supervisor_engine_api_staging_evidence(_read(evidence_file, 4096))
        if evidence.environment_id != expected_environment: raise ManifestHandoffRegistryUnavailable
        current = now or datetime.now(timezone.utc)
        if not isinstance(current, datetime) or current.tzinfo is None: raise ManifestHandoffRegistryUnavailable
        observed = datetime.fromisoformat(evidence.observed_at.replace("Z", "+00:00"))
        age = (current.astimezone(timezone.utc) - observed).total_seconds()
        if age < 0 or age > maximum_age_seconds: raise ManifestHandoffRegistryUnavailable
        expected = (evidence.render_sha256, evidence.inspect_sha256, evidence.health_sha256, evidence.policy_sha256, evidence.shutdown_sha256)
        actual = tuple(hashlib.sha256(_read(path, _MAX_ARTIFACT_BYTES)).hexdigest() for path in paths[1:])
        if actual != expected: raise ManifestHandoffRegistryUnavailable
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None

def main(argv=None):
    parser=argparse.ArgumentParser(add_help=False)
    for name in ("evidence-file","render-file","inspect-file","health-file","policy-file","shutdown-file"): parser.add_argument(f"--{name}",required=True,type=Path)
    parser.add_argument("--expected-environment",required=True); parser.add_argument("--maximum-age-seconds",required=True,type=int)
    try:
        value=parser.parse_args(argv); verify(value.evidence_file,value.render_file,value.inspect_file,value.health_file,value.policy_file,value.shutdown_file,expected_environment=value.expected_environment,maximum_age_seconds=value.maximum_age_seconds); return 0
    except Exception: return 2

if __name__ == "__main__": raise SystemExit(main())
