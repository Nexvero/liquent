"""Read-only verifier for one private joint Engine API staging evidence artifact."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import stat
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_evidence import decode_manifest_handoff_supervisor_engine_api_staging_evidence

def verify(path: Path) -> None:
    descriptor = None
    try:
        if not isinstance(path, Path) or not path.is_absolute() or path == Path("/") or ".." in path.parts: raise ManifestHandoffRegistryUnavailable
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        facts = os.fstat(descriptor)
        if not stat.S_ISREG(facts.st_mode) or facts.st_uid != os.geteuid() or stat.S_IMODE(facts.st_mode) != 0o600 or facts.st_nlink != 1 or facts.st_size < 1 or facts.st_size > 4096 or os.get_inheritable(descriptor): raise ManifestHandoffRegistryUnavailable
        content = os.read(descriptor, 4097)
        if len(content) != facts.st_size: raise ManifestHandoffRegistryUnavailable
        decode_manifest_handoff_supervisor_engine_api_staging_evidence(content)
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
    finally:
        if descriptor is not None:
            try: os.close(descriptor)
            except Exception: pass

def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False); parser.add_argument("--evidence-file", required=True, type=Path)
    try: verify(parser.parse_args(argv).evidence_file); return 0
    except Exception: return 2

if __name__ == "__main__": raise SystemExit(main())
