"""Minimal CLI presentation for reconciliation settings installation."""

from pathlib import Path
import sys
from typing import TextIO

from liquent_platform.transport.staging_research_index_promotion_reconciliation_settings_installer import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome,
    install_staging_research_index_promotion_reconciliation_settings,
)


def run(
    argv: tuple[str, ...],
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    """Return the fixed, detail-free result of one installation attempt."""

    try:
        if (
            type(argv) is not tuple
            or len(argv) != 4
            or any(type(value) is not str for value in argv)
        ):
            stderr.write("invalid_invocation\n")
            return 2
        paths = tuple(Path(value) for value in argv)
        if any(
            not path.is_absolute()
            or path == Path("/")
            or ".." in path.parts
            or path.name in {"", ".", ".."}
            or len(str(path)) > 4096
            for path in paths
        ):
            stderr.write("invalid_invocation\n")
            return 2
        outcome = install_staging_research_index_promotion_reconciliation_settings(
            paths[0], paths[1], paths[2], paths[3]
        )
        if (
            outcome
            is StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome.INSTALLED
        ):
            stdout.write("installed\n")
            return 0
        if (
            outcome
            is StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome.PRESENT
        ):
            stderr.write("present\n")
            return 3
    except Exception:
        pass
    stderr.write("unavailable\n")
    return 1


def main() -> None:
    raise SystemExit(run(tuple(sys.argv[1:]), stdout=sys.stdout, stderr=sys.stderr))
