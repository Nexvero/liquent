#!/usr/bin/env python3
"""Fail-closed structural verification for the generated SPDX JSON SBOM."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


FORBIDDEN_FRAGMENTS = (
    "/operations/secrets/",
    "/data/raw/",
    "/data/processed/",
    "/run/secrets/",
    "/.env",
)


def _fail(message: str) -> None:
    raise SystemExit(f"SBOM verification failed: {message}")


def verify(path: Path) -> str:
    try:
        raw = path.read_bytes()
        document: dict[str, Any] = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read valid JSON: {exc}")

    if document.get("spdxVersion") not in {"SPDX-2.2", "SPDX-2.3"}:
        _fail("unsupported or missing SPDX version")
    if document.get("SPDXID") != "SPDXRef-DOCUMENT":
        _fail("missing SPDX document identity")
    if not str(document.get("documentNamespace", "")).startswith(("https://", "http://")):
        _fail("missing document namespace")

    packages = document.get("packages")
    if not isinstance(packages, list) or not packages:
        _fail("package inventory is empty")
    names = {str(package.get("name", "")).lower() for package in packages if isinstance(package, dict)}
    if "liquent" not in names:
        _fail("Liquent package identity is absent")

    flattened = raw.decode("utf-8", errors="replace").lower()
    for fragment in FORBIDDEN_FRAGMENTS:
        if fragment.lower() in flattened:
            _fail(f"forbidden path or secret suffix present: {fragment}")

    digest = hashlib.sha256(raw).hexdigest()
    print(f"sbom={path.name}")
    print(f"packages={len(packages)}")
    print(f"sha256={digest}")
    return digest


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_image_sbom.py SBOM.spdx.json")
    verify(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
