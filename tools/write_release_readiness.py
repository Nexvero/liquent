#!/usr/bin/env python3
"""Write non-authorizing release-candidate readiness evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__:
    from .validate_release_candidate import validate_metadata, validate_quality_evidence
else:
    from validate_release_candidate import validate_metadata, validate_quality_evidence


def build_readiness(
    revision: str, version: str, evidence: dict[str, Any]
) -> dict[str, object]:
    validate_metadata(revision, version)
    validate_quality_evidence(revision, evidence)
    return {
        "schema_version": 1,
        "candidate": {"revision": revision, "version": version},
        "quality_gate": {
            "workflow": ".github/workflows/quality.yml",
            "event": "push",
            "branch": "main",
            "conclusion": "success",
            "verified": True,
        },
        "publication": {
            "authorized": False,
            "performed": False,
            "required_confirmation": "PUBLISH",
            "workflow": ".github/workflows/release.yml",
        },
        "deployment": {"authorized": False, "performed": False},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--quality-runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence = json.loads(args.quality_runs.read_text(encoding="utf-8"))
    try:
        readiness = build_readiness(args.revision, args.version, evidence)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(readiness, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"release readiness verified: {args.version} @ {args.revision}")


if __name__ == "__main__":
    main()
