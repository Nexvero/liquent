from io import StringIO
from pathlib import Path

import pytest

from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_cli as cli,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_process_outcome import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationProcessOutcome,
)


@pytest.mark.parametrize(
    "outcome,expected",
    [
        (StagingResearchIndexPromotionReconciliationProcessOutcome.IDLE, "idle\n"),
        (
            StagingResearchIndexPromotionReconciliationProcessOutcome.RECONCILED,
            "reconciled\n",
        ),
    ],
)
def test_success_outcomes_use_fixed_stdout_and_zero_exit(
    monkeypatch, outcome, expected
) -> None:
    calls = []
    monkeypatch.setattr(
        cli,
        "observe_staging_research_index_promotion_reconciliation_process_outcome",
        lambda path: calls.append(path) or outcome,
    )
    stdout, stderr = StringIO(), StringIO()
    code = cli.run(
        ("/run/liquent/reconciliation.env",), stdout=stdout, stderr=stderr
    )
    assert code == 0 and stdout.getvalue() == expected and stderr.getvalue() == ""
    assert calls == [Path("/run/liquent/reconciliation.env")]


def test_technical_failure_is_fixed_stderr_and_exit_one(monkeypatch) -> None:
    def unavailable(_path):
        raise RuntimeError("database password detail")

    monkeypatch.setattr(
        cli,
        "observe_staging_research_index_promotion_reconciliation_process_outcome",
        unavailable,
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(
        ("/run/liquent/reconciliation.env",), stdout=stdout, stderr=stderr
    ) == 1
    assert stdout.getvalue() == "" and stderr.getvalue() == "unavailable\n"
    assert "password" not in stderr.getvalue()


@pytest.mark.parametrize(
    "argv",
    [(), ("relative.env",), ("/",), ("/run/../secret.env",), ("/a", "/b"), ["/a"]],
)
def test_invalid_invocation_never_calls_process_and_exits_two(monkeypatch, argv) -> None:
    calls = []
    monkeypatch.setattr(
        cli,
        "observe_staging_research_index_promotion_reconciliation_process_outcome",
        lambda path: calls.append(path),
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(argv, stdout=stdout, stderr=stderr) == 2
    assert stdout.getvalue() == "" and stderr.getvalue() == "invalid_invocation\n"
    assert calls == []


def test_unknown_outcome_fails_closed() -> None:
    stdout, stderr = StringIO(), StringIO()
    original = cli.observe_staging_research_index_promotion_reconciliation_process_outcome
    try:
        cli.observe_staging_research_index_promotion_reconciliation_process_outcome = (
            lambda _: object()
        )
        assert cli.run(("/run/liquent/x.env",), stdout=stdout, stderr=stderr) == 1
    finally:
        cli.observe_staging_research_index_promotion_reconciliation_process_outcome = original
    assert stderr.getvalue() == "unavailable\n"
