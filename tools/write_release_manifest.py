#!/usr/bin/env python3
"""Write deterministic release evidence after a successful registry push."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.digest):
        parser.error("digest must be a complete sha256 digest")
    sbom_digest = hashlib.sha256(args.sbom.read_bytes()).hexdigest()
    document = {
        "schema": "liquent.release-evidence.v1",
        "revision": args.revision,
        "version": args.version,
        "image": args.image,
        "image_digest": args.digest,
        "sbom_sha256": sbom_digest,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
