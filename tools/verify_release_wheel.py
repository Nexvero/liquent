"""Fail-closed verification of the installable Liquent Python artifact."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import re
import zipfile


REQUIRED_FILES = {
    "liquent_platform/persistence/alembic/env.py",
    "liquent_platform/persistence/alembic/script.py.mako",
    "liquent_platform/persistence/alembic/versions/20260726_0001_platform_baseline.py",
}
REQUIRED_ENTRY_POINTS = {
    "liquent-control-plane = liquent_platform.transport.http.main:main",
    "liquent-health-check = liquent_platform.observability.external_health:main",
    "liquent-migrate = liquent_platform.persistence.migrate:main",
}
FORBIDDEN_NAME_PARTS = {
    ".env",
    ".key",
    ".pem",
    "data/raw",
    "data/processed",
    "operations/secrets",
    "reports/",
}


def verify_wheel(path: Path) -> str:
    if not path.is_file() or path.suffix != ".whl":
        raise ValueError("expected exactly one wheel file")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = REQUIRED_FILES.difference(names)
        if missing:
            raise ValueError(f"wheel is missing required files: {sorted(missing)}")
        forbidden = sorted(
            name
            for name in names
            if any(part.lower() in name.lower() for part in FORBIDDEN_NAME_PARTS)
        )
        if forbidden:
            raise ValueError(f"wheel contains forbidden paths: {forbidden}")
        entry_point_files = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
        if len(entry_point_files) != 1:
            raise ValueError("wheel must contain exactly one entry_points.txt")
        entry_points = archive.read(entry_point_files[0]).decode("utf-8")
        for entry_point in REQUIRED_ENTRY_POINTS:
            if not re.search(rf"^{re.escape(entry_point)}$", entry_points, re.MULTILINE):
                raise ValueError(f"wheel is missing entry point: {entry_point}")
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    digest = verify_wheel(args.wheel)
    print(f"wheel={args.wheel.name}")
    print(f"sha256={digest}")


if __name__ == "__main__":
    main()
