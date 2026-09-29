"""Detail-free CLI for the staging reconciliation candidate audit."""

from pathlib import Path
import sys
from typing import TextIO

from liquent_platform.transport.staging_research_index_promotion_reconciliation_candidate_audit import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationCandidateAudit,
    audit_staging_research_index_promotion_reconciliation_candidate,
)


def run(
    argv: tuple[str, ...],
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Return one fixed candidate-state token without exposing identity."""

    try:
        if type(argv) is not tuple or len(argv) != 1 or type(argv[0]) is not str:
            stderr.write("invalid_invocation\n")
            return 2
        path = Path(argv[0])
        if not path.is_absolute() or path == Path("/") or ".." in path.parts:
            stderr.write("invalid_invocation\n")
            return 2
        outcome = audit_staging_research_index_promotion_reconciliation_candidate(
            path
        )
        if outcome is StagingResearchIndexPromotionReconciliationCandidateAudit.PENDING:
            stdout.write("pending\n")
            return 0
        if outcome is StagingResearchIndexPromotionReconciliationCandidateAudit.IDLE:
            stdout.write("idle\n")
            return 0
    except Exception:
        pass
    stderr.write("unavailable\n")
    return 1


def main() -> None:
    raise SystemExit(run(tuple(sys.argv[1:]), stdout=sys.stdout, stderr=sys.stderr))
