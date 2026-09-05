#!/usr/bin/env python3
"""Explicit local composition for one controlled, non-publishing preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from tools.controlled_release_preflight import (
    ControlledPreflightRejected,
    ControlledReleasePreflight,
)
from tools.local_release_preflight_gates import (
    LocalGateContext,
    local_gate_adapters,
)


def compose_local_preflight(source_root: Path) -> ControlledReleasePreflight:
    """Bind the fixed local adapters without running or authorizing them."""

    context = LocalGateContext(source_root)
    return ControlledReleasePreflight(local_gate_adapters(context))


def run_local_preflight(source_root: Path, output_directory: Path) -> Path:
    """Run once; the coordinator owns atomic output publication."""

    return compose_local_preflight(source_root).run(output_directory)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="controlled-release-preflight")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evidence = run_local_preflight(args.source_root, args.output_directory)
    except ControlledPreflightRejected:
        print(json.dumps({"error": "controlled_release_preflight_rejected"}))
        return 2
    print(
        json.dumps(
            {
                "evidence": evidence.name,
                "outcome": "passed",
                "publishing_authorized": False,
                "deployment_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
