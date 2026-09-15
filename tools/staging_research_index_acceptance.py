"""Offline tool for sanitized staging Research-index acceptance input."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import stat
import sys

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
    StagingResearchIndexObservation,
    evaluate_staging_research_index_acceptance,
)

_MAX_INPUT_BYTES = 16_384


def _load(path: Path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise ValueError("acceptance input must be an owner-private regular file")
    content = path.read_bytes()
    if not content or len(content) > _MAX_INPUT_BYTES:
        raise ValueError("acceptance input size is invalid")
    value = json.loads(content)
    expected = {"candidate_digest", "staging_origin", "observed_at", "observations"}
    if type(value) is not dict or set(value) != expected:
        raise ValueError("acceptance input shape is invalid")
    run = StagingResearchIndexAcceptanceRun(
        value["candidate_digest"],
        value["staging_origin"],
        datetime.fromisoformat(value["observed_at"]),
    )
    if type(value["observations"]) is not list:
        raise ValueError("acceptance observations must be a list")
    observations = []
    for item in value["observations"]:
        if type(item) is not dict or set(item) != {"check", "outcome"}:
            raise ValueError("acceptance observation shape is invalid")
        observations.append(
            StagingResearchIndexObservation(
                StagingResearchIndexCheck(item["check"]),
                StagingResearchIndexCheckOutcome(item["outcome"]),
            )
        )
    return run, tuple(observations)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="staging-research-index-acceptance")
    parser.add_argument("--input", required=True, type=Path)
    try:
        arguments = parser.parse_args(argv)
        run, observations = _load(arguments.input)
        result = evaluate_staging_research_index_acceptance(run, observations)
        output = {
            "candidate_digest": run.candidate_digest,
            "staging_origin": run.staging_origin,
            "observed_at": run.observed_at.isoformat(),
            "outcome": result.outcome.value,
        }
        sys.stdout.write(json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n")
        return {
            StagingResearchIndexAcceptanceOutcome.ACCEPTED: 0,
            StagingResearchIndexAcceptanceOutcome.REJECTED: 3,
            StagingResearchIndexAcceptanceOutcome.UNAVAILABLE: 4,
        }[result.outcome]
    except SystemExit as error:
        return int(error.code)
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
