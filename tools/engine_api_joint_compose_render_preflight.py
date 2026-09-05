"""Read-only Docker Compose render preflight for the opt-in Engine API overlay."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable

def verify(base_file: Path, overlay_file: Path, environment_file: Path, *, timeout_seconds: int = 30) -> None:
    try:
        files = (base_file, overlay_file, environment_file)
        if (any(not isinstance(path, Path) or not path.is_absolute() or path == Path("/") or ".." in path.parts for path in files)
                or type(timeout_seconds) is not int or timeout_seconds < 1 or timeout_seconds > 120):
            raise ManifestHandoffRegistryUnavailable
        result = subprocess.run(("docker", "compose", "--env-file", str(environment_file), "-f", str(base_file), "-f", str(overlay_file), "--profile", "supervisor-engine-api", "config", "--quiet"), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout_seconds, check=False, shell=False)
        if type(result) is not subprocess.CompletedProcess or result.returncode != 0:
            raise ManifestHandoffRegistryUnavailable
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--base-file", required=True, type=Path)
    parser.add_argument("--overlay-file", required=True, type=Path)
    parser.add_argument("--environment-file", required=True, type=Path)
    try:
        values = parser.parse_args(argv)
        verify(values.base_file, values.overlay_file, values.environment_file)
        return 0
    except Exception:
        return 2

if __name__ == "__main__": raise SystemExit(main())
