from io import StringIO
from pathlib import Path

import pytest

from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_candidate_audit_cli as cli,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_candidate_audit import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationCandidateAudit,
)


@pytest.mark.parametrize(
    ("outcome", "token"),
    [
        (StagingResearchIndexPromotionReconciliationCandidateAudit.PENDING, "pending\n"),
        (StagingResearchIndexPromotionReconciliationCandidateAudit.IDLE, "idle\n"),
    ],
)
def test_fixed_success_token_and_zero_exit(monkeypatch, outcome, token) -> None:
    calls = []
    monkeypatch.setattr(
        cli,
        "audit_staging_research_index_promotion_reconciliation_candidate",
        lambda path: calls.append(path) or outcome,
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(
        ("/run/liquent/reconciliation.env",), stdout=stdout, stderr=stderr
    ) == 0
    assert stdout.getvalue() == token and stderr.getvalue() == ""
    assert calls == [Path("/run/liquent/reconciliation.env")]


def test_failure_is_detail_free_stderr_and_exit_one(monkeypatch) -> None:
    def unavailable(_path):
        raise RuntimeError("operation-id-private")

    monkeypatch.setattr(
        cli,
        "audit_staging_research_index_promotion_reconciliation_candidate",
        unavailable,
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(("/run/liquent/x.env",), stdout=stdout, stderr=stderr) == 1
    assert stdout.getvalue() == "" and stderr.getvalue() == "unavailable\n"
    assert "operation-id-private" not in stderr.getvalue()


@pytest.mark.parametrize(
    "argv",
    [(), ("relative.env",), ("/",), ("/run/../secret.env",), ("/a", "/b"), ["/a"]],
)
def test_invalid_invocation_never_calls_audit(monkeypatch, argv) -> None:
    calls = []
    monkeypatch.setattr(
        cli,
        "audit_staging_research_index_promotion_reconciliation_candidate",
        lambda path: calls.append(path),
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(argv, stdout=stdout, stderr=stderr) == 2
    assert stdout.getvalue() == "" and stderr.getvalue() == "invalid_invocation\n"
    assert calls == []


def test_unknown_outcome_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "audit_staging_research_index_promotion_reconciliation_candidate",
        lambda _path: object(),
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(("/run/liquent/x.env",), stdout=stdout, stderr=stderr) == 1
    assert stdout.getvalue() == "" and stderr.getvalue() == "unavailable\n"
