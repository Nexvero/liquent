#!/usr/bin/env python3
"""Validate manual release inputs against completed quality workflow evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


REVISION_RE = re.compile(r"[0-9a-f]{40}")
VERSION_RE = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")


def validate(revision: str, version: str, confirmation: str, evidence: dict[str, Any]) -> None:
    if not REVISION_RE.fullmatch(revision):
        raise ValueError("revision must be a lowercase 40-character commit SHA")
    if not VERSION_RE.fullmatch(version):
        raise ValueError("version must use strict X.Y.Z syntax")
    if confirmation != "PUBLISH":
        raise ValueError("confirmation must equal PUBLISH")

    runs = evidence.get("workflow_runs")
    if not isinstance(runs, list):
        raise ValueError("quality evidence has no workflow_runs list")
    accepted = any(
        isinstance(run, dict)
        and run.get("head_sha") == revision
        and run.get("path") == ".github/workflows/quality.yml"
        and run.get("event") == "push"
        and run.get("head_branch") == "main"
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        for run in runs
    )
    if not accepted:
        raise ValueError("no successful completed main-push quality run for revision")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--quality-runs", type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.quality_runs.read_text(encoding="utf-8"))
    try:
        validate(args.revision, args.version, args.confirmation, evidence)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"release candidate accepted: {args.version} @ {args.revision}")


if __name__ == "__main__":
    main()
