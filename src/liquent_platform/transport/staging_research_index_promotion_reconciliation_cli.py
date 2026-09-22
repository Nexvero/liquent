"""Minimal CLI presentation for one staging promotion reconciliation."""

from pathlib import Path
import sys
from typing import TextIO

from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_outcome import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessOutcome,
    observe_staging_research_index_promotion_reconciliation_process_outcome,
)


def run(
    argv: tuple[str, ...],
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Return stable exit status and fixed detail-free output."""

    try:
        if type(argv) is not tuple or len(argv) != 1 or type(argv[0]) is not str:
            stderr.write("invalid_invocation\n")
            return 2
        path = Path(argv[0])
        if not path.is_absolute() or path == Path("/") or ".." in path.parts:
            stderr.write("invalid_invocation\n")
            return 2
        outcome = observe_staging_research_index_promotion_reconciliation_process_outcome(
            path
        )
        if outcome is StagingResearchIndexPromotionReconciliationProcessOutcome.IDLE:
            stdout.write("idle\n")
            return 0
        if outcome is StagingResearchIndexPromotionReconciliationProcessOutcome.RECONCILED:
            stdout.write("reconciled\n")
            return 0
    except Exception:
        pass
    stderr.write("unavailable\n")
    return 1


def main() -> None:
    raise SystemExit(run(tuple(sys.argv[1:]), stdout=sys.stdout, stderr=sys.stderr))
